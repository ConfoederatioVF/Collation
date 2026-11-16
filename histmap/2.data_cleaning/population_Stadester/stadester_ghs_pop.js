//Initialise functions
{
  if (!global.population_Stadester_ghs_pop) global.population_Stadester_ghs_pop = {};
  if (!global.population_Stadester_config && typeof require !== "undefined")
    try { require(path.join(__dirname, "config", "stadester_config.js")); } catch (e) {}
  
  /**
   * Builds modern-eligible Stadestér settlement descriptor entries and spatial grid index for GHSL/GHS-POP integration.
   * @alias population_Stadester_ghs_pop.buildGHSLCityEntries
   * 
   * @param {Object} arg0_stadester_obj
   * @param {Object} [arg1_options]
   * 
   * @returns {{city_entries: Array<Object>, city_grid: Map<string, Array<number>>}}
   */
  population_Stadester_ghs_pop.buildGHSLCityEntries = function (arg0_stadester_obj, arg1_options) {
    //Convert from parameters
    let stadester_obj = arg0_stadester_obj;
    let options = (arg1_options) ? arg1_options : {};
    
    //Declare local instance variables
    let all_city_keys;
    let cfg = global.population_Stadester_config;
    let city_entries = [];
    let city_grid = new Map();
    let cutoff_year = (options.cutoff_year !== undefined) ?
      options.cutoff_year : ((cfg && cfg.cutoff_year !== undefined) ? cfg.cutoff_year : 1975);
    
    //Guard clauses
    if (!stadester_obj) return { city_entries: city_entries, city_grid: city_grid };
    
    //Function body
    all_city_keys = Object.keys(stadester_obj);
    for (let i = 0; i < all_city_keys.length; i++) {
      let local_city = stadester_obj[all_city_keys[i]];
      if (!population_Stadester_ghs_pop.isModernEligibleSettlement(local_city, all_city_keys[i], { cutoff_year: cutoff_year }))
        continue;
      
      let bounds = population_Stadester_ghs_pop.getEmpiricalBounds(local_city);
      let found_yr = parseInt(local_city["found.yr"], 10);
      let lat = Number(local_city.coords[0]);
      let lng = Number(local_city.coords[1]);
      let manual_pop_backup = (local_city.type === "manual" && local_city.population) ? Object.assign({}, local_city.population) : null;
      let px = Math.min(4319, Math.max(0, Math.floor(((lng + 180)/360)*4320)));
      let py = Math.min(2159, Math.max(0, Math.floor(((90 - lat)/180)*2160)));
      let cell_key = `${Math.floor(lng)},${Math.floor(lat)}`;
      let entry_idx = city_entries.length;
      let war_pop_backup = {};
      let war_years_set = null;
      
      if (Array.isArray(local_city._war_displacement_years) && local_city._war_displacement_years.length > 0) {
        war_years_set = new Set(local_city._war_displacement_years.map(Number).filter(n => !isNaN(n)));
        if (local_city.population) {
          for (let w_yr of war_years_set) {
            if (local_city.population[w_yr] !== undefined)
              war_pop_backup[w_yr] = local_city.population[w_yr];
          }
        }
      }
      
      city_entries.push({
        city: local_city,
        epoch_cluster: {},
        found_yr: found_yr,
        has_ucdb: false,
        is_suppressed_non_ucdb_twin: false,
        is_suppressed_ucdb_twin: false,
        key: all_city_keys[i],
        lat: lat,
        lng: lng,
        manual_pop_backup: manual_pop_backup,
        norm_names: population_Stadester_ghsl.getNormalisedCityNames(local_city),
        px: px,
        py: py,
        raw_max_year: bounds.raw_max_year,
        raw_min_year: bounds.raw_min_year,
        raw_pop: (local_city.population) ? Object.assign({}, local_city.population) : {},
        ucdb_pop_by_year: {},
        ucdb_weight_by_year: {},
        war_pop_backup: war_pop_backup,
        war_years_set: war_years_set
      });
      
      if (!city_grid.has(cell_key)) city_grid.set(cell_key, []);
      city_grid.get(cell_key).push(entry_idx);
    }
    
    //Return statement
    return { city_entries: city_entries, city_grid: city_grid };
  };
  
  /**
   * Removes transient pipeline tracking properties from all cities before JSON serialisation.
   * @alias population_Stadester_ghs_pop.cleanTransientMetadata
   * 
   * @param {Object} arg0_stadester_obj
   * 
   * @returns {Object}
   */
  population_Stadester_ghs_pop.cleanTransientMetadata = function (arg0_stadester_obj) {
    //Convert from parameters
    let stadester_obj = arg0_stadester_obj;
    
    //Declare local instance variables
    let all_keys;
    let transient_keys = [
      "_max_yr", "_min_yr", "_pop_keys", "_pop_keys_sorted", "_px",
      "_raw_lapsed", "_raw_max_year", "_raw_min_year", "_war_displacement_years"
    ];
    
    //Guard clauses
    if (!stadester_obj || typeof stadester_obj !== "object") return stadester_obj;
    
    //Function body
    all_keys = Object.keys(stadester_obj);
    for (let i = 0; i < all_keys.length; i++) {
      let city = stadester_obj[all_keys[i]];
      if (!city || typeof city !== "object") continue;
      for (let x = 0; x < transient_keys.length; x++)
        if (city[transient_keys[x]] !== undefined)
          delete city[transient_keys[x]];
    }
    
    //Return statement
    return stadester_obj;
  };
  
  /**
   * Distributes a gridcell population across active settlements using deterministic largest-remainder integer rounding.
   * @alias population_Stadester_ghs_pop.distributeCellShare
   * 
   * @param {number} arg0_cell_pop
   * @param {number} arg1_n_active
   * @param {Array<Object>} arg2_targets
   * 
   * @returns {Map<Object, number>}
   */
  population_Stadester_ghs_pop.distributeCellShare = function (arg0_cell_pop, arg1_n_active, arg2_targets) {
    //Convert from parameters
    let cell_pop = Math.max(0, Number(arg0_cell_pop) || 0);
    let n_active = Math.max(1, parseInt(arg1_n_active) || 1);
    let targets = Array.isArray(arg2_targets) ? arg2_targets : [];
    
    //Declare local instance variables
    let allocations = new Map();
    let exact_share = cell_pop/n_active;
    let floor_share;
    let remainder;
    let sorted_targets;
    let target_int_sum;
    
    //Guard clauses
    if (targets.length === 0) return allocations;
    
    //Function body
    if (targets.length === n_active && n_active > 1) {
      target_int_sum = Math.max(0, Math.round(cell_pop));
      floor_share = Math.floor(target_int_sum/n_active);
      remainder = target_int_sum - floor_share*n_active;
      sorted_targets = targets.slice().sort(function (a, b) {
        return String(a.key || "").localeCompare(String(b.key || ""));
      });
      
      for (let i = 0; i < sorted_targets.length; i++)
        allocations.set(sorted_targets[i], floor_share + ((i < remainder) ? 1 : 0));
    } else {
      let rounded_share = Math.max(0, Math.round(exact_share));
      for (let i = 0; i < targets.length; i++)
        allocations.set(targets[i], rounded_share);
    }
    
    //Return statement
    return allocations;
  };
  
  /**
   * Resolves true empirical year bounds and lapse status for a Stadestér settlement.
   * @alias population_Stadester_ghs_pop.getEmpiricalBounds
   * 
   * @param {Object} arg0_city
   * 
   * @returns {{is_lapsed: boolean, raw_max_year: number|null, raw_min_year: number|null}}
   */
  population_Stadester_ghs_pop.getEmpiricalBounds = function (arg0_city) {
    //Convert from parameters
    let city = arg0_city;
    
    //Declare local instance variables
    let all_yrs = [];
    let is_lapsed = false;
    let pos_yrs = [];
    let raw_max_year = null;
    let raw_min_year = null;
    
    //Guard clauses
    if (!city || !city.population)
      return { is_lapsed: true, raw_max_year: null, raw_min_year: null };
    
    //Function body
    if (city._raw_lapsed === true || Number(city.population["-999"]) === 0)
      is_lapsed = true;
    
    if (Number.isFinite(city._raw_min_year) && Number.isFinite(city._raw_max_year)) {
      raw_min_year = city._raw_min_year;
      raw_max_year = city._raw_max_year;
    } else {
      all_yrs = Object.keys(city.population).map(Number).filter(n => !isNaN(n)).sort((a, b) => a - b);
      for (let i = 0; i < all_yrs.length; i++) {
        let val = Array.isArray(city.population[all_yrs[i]]) ?
          Number(city.population[all_yrs[i]][0]) : Number(city.population[all_yrs[i]]);
        if (Number.isFinite(val) && val > 0)
          pos_yrs.push(all_yrs[i]);
      }
      if (pos_yrs.length > 0) {
        raw_min_year = pos_yrs[0];
        raw_max_year = pos_yrs[pos_yrs.length - 1];
      } else {
        is_lapsed = true;
      }
      if (all_yrs.length > 0) {
        let last_yr = all_yrs[all_yrs.length - 1];
        let last_val = Array.isArray(city.population[last_yr]) ?
          Number(city.population[last_yr][0]) : Number(city.population[last_yr]);
        if (!Number.isFinite(last_val) || last_val <= 0)
          is_lapsed = true;
      }
    }
    
    //Return statement
    return {
      is_lapsed: is_lapsed,
      raw_max_year: raw_max_year,
      raw_min_year: raw_min_year
    };
  };
  
  /**
   * Determines dynamically whether a Stadestér settlement is active in the modern era (1975-2025).
   * Admits both post-1975 settlements and earlier settlements within the HYDE-aware hiatus window (>=200 years min).
   * @alias population_Stadester_ghs_pop.isModernEligibleSettlement
   * 
   * @param {Object} arg0_city
   * @param {string} [arg1_key]
   * @param {Object} [arg2_options]
   *  @param {number} [arg2_options.cutoff_year=1975]
   * 
   * @returns {boolean}
   */
  population_Stadester_ghs_pop.isModernEligibleSettlement = function (arg0_city, arg1_key, arg2_options) {
    //Convert from parameters
    let city = arg0_city;
    let key = arg1_key;
    let options = (arg2_options) ? arg2_options : {};
    
    //Declare local instance variables
    let bounds;
    let cfg = global.population_Stadester_config;
    let cutoff_year = (options.cutoff_year !== undefined) ?
      options.cutoff_year : ((cfg && cfg.cutoff_year !== undefined) ? cfg.cutoff_year : 1975);
    let key_str;
    let lat;
    let lng;
    let max_gap;
    
    //Guard clauses
    if (!city || !Array.isArray(city.coords) || city.coords.length < 2) return false;
    lat = Number(city.coords[0]);
    lng = Number(city.coords[1]);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return false;
    
    bounds = population_Stadester_ghs_pop.getEmpiricalBounds(city);
    if (bounds.is_lapsed || !Number.isFinite(bounds.raw_max_year)) return false;
    
    if (city.modern_active === true) return true;
    
    key_str = String(key || city.key || "");
    if (key_str.includes("_chandler_modelski") && bounds.raw_max_year < cutoff_year) return false;
    if (bounds.raw_max_year >= cutoff_year) return true;
    
    max_gap = (typeof population_Stadester_uud !== "undefined" && typeof population_Stadester_uud.getMaxTemporalProximityGap === "function") ?
      population_Stadester_uud.getMaxTemporalProximityGap(bounds.raw_max_year, cutoff_year) : 200;
    
    //Return statement
    return (cutoff_year - bounds.raw_max_year) <= max_gap;
  };
  
  /**
   * Builds a complete GHS-UCDB lookup map from ghsl.json backfilled with any missing clusters from GHS_UCDB_MTUC_GLOBE_R2024A.csv.
   * @alias population_Stadester_ghs_pop.loadCompleteUCDBMap
   * 
   * @param {Object} arg0_ghsl_obj
   * @param {Object} [arg1_options]
   * 
   * @returns {Map<number, Object>}
   */
  population_Stadester_ghs_pop.loadCompleteUCDBMap = function (arg0_ghsl_obj, arg1_options) {
    //Convert from parameters
    let ghsl_obj = arg0_ghsl_obj;
    let options = (arg1_options) ? arg1_options : {};
    
    //Declare local instance variables
    let all_ghsl_keys;
    let area_cols = {};
    let backfilled_count = 0;
    let cfg = global.population_Stadester_config;
    let country_idx;
    let epochs = [1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025];
    let ghsl_by_id = new Map();
    let headers;
    let id_idx;
    let lines;
    let name_idx;
    let pop_cols = {};
    let raw_text;
    let ucdb_candidates;
    let ucdb_csv_path = null;
    
    //Function body
    if (ghsl_obj) {
      all_ghsl_keys = Object.keys(ghsl_obj);
      for (let i = 0; i < all_ghsl_keys.length; i++) {
        let local_ghsl = ghsl_obj[all_ghsl_keys[i]];
        if (local_ghsl && local_ghsl.id)
          ghsl_by_id.set(Number(local_ghsl.id), local_ghsl);
      }
    }
    
    ucdb_candidates = [
      options.ucdb_csv_path,
      cfg && cfg.ucdb_csv_path,
      path.join((typeof h1 !== "undefined") ? h1 : "./histmap/1.data_raw", "population_GHSL", "GHS_UCDB_MTUC_GLOBE_R2024A.csv"),
      "./histmap/1.data_raw/population_GHSL/GHS_UCDB_MTUC_GLOBE_R2024A.csv"
    ];
    for (let i = 0; i < ucdb_candidates.length; i++) {
      if (ucdb_candidates[i] && fs.existsSync(ucdb_candidates[i])) {
        ucdb_csv_path = ucdb_candidates[i];
        break;
      }
    }
    
    if (ucdb_csv_path) {
      raw_text = fs.readFileSync(ucdb_csv_path, "utf8").replace(/^\uFEFF/, "");
      lines = raw_text.split(/\r?\n/);
      if (lines.length > 1) {
        headers = lines[0].split(";").map(s => s.trim());
        id_idx = headers.indexOf("ID_MTUC_G0");
        if (id_idx < 0) id_idx = 0;
        name_idx = headers.indexOf("GC_UCN_MAI_2025");
        if (name_idx < 0) name_idx = 1;
        country_idx = headers.indexOf("GC_CNT_GAD_2025");
        if (country_idx < 0) country_idx = 3;
        
        for (let i = 0; i < epochs.length; i++) {
          let ep = epochs[i];
          pop_cols[ep] = headers.indexOf(`MT_POP_TOT_${ep}`);
          area_cols[ep] = headers.indexOf(`MT_UCA_KM2_${ep}`);
        }
        
        for (let i = 1; i < lines.length; i++) {
          let line = lines[i].trim();
          if (!line) continue;
          let cols = line.split(";");
          let uc_id = Number(cols[id_idx]);
          if (!Number.isFinite(uc_id) || uc_id <= 0 || ghsl_by_id.has(uc_id)) continue;
          
          let area_obj = {};
          let has_positive_pop = false;
          let pop_obj = {};
          
          for (let x = 0; x < epochs.length; x++) {
            let ep = epochs[x];
            let p_idx = pop_cols[ep];
            let a_idx = area_cols[ep];
            if (p_idx >= 0 && cols[p_idx] !== undefined) {
              let p_clean = String(cols[p_idx]).trim().replace(/\./g, "").replace(",", ".");
              let p_val = parseFloat(p_clean);
              if (Number.isFinite(p_val) && p_val > 0) {
                pop_obj[ep] = Math.round(p_val);
                has_positive_pop = true;
              }
            }
            if (a_idx >= 0 && cols[a_idx] !== undefined) {
              let a_clean = String(cols[a_idx]).trim().replace(/\./g, "").replace(",", ".");
              let a_val = parseFloat(a_clean);
              if (Number.isFinite(a_val) && a_val > 0)
                area_obj[ep] = a_val;
            }
          }
          
          if (has_positive_pop) {
            let uc_country = (cols[country_idx] && cols[country_idx] !== "#N/A") ? String(cols[country_idx]).trim() : "";
            let uc_name = (cols[name_idx] && cols[name_idx] !== "N/A") ? String(cols[name_idx]).trim() : `ghsl-${uc_id}`;
            ghsl_by_id.set(uc_id, {
              area: area_obj,
              country: uc_country,
              id: uc_id,
              key: uc_country ? `${uc_name}-${uc_country}` : `ghsl-${uc_id}`,
              name: uc_name,
              population: pop_obj
            });
            backfilled_count++;
          }
        }
      }
      if (backfilled_count > 0)
        console.log(`- Backfilled ${backfilled_count} missing GHS-UCDB clusters from CSV (total ${ghsl_by_id.size} clusters).`);
    }
    
    //Return statement
    return ghsl_by_id;
  };
  
  /**
   * Loads land area mask and reference GHS_POP_2020 raster for coastal pixel snapping.
   * @alias population_Stadester_ghs_pop.loadLandAndReferenceRasters
   * 
   * @param {Object} [arg0_options]
   * 
   * @returns {{land_data: Uint32Array|null, ref_pop_data: Float32Array|null}}
   */
  population_Stadester_ghs_pop.loadLandAndReferenceRasters = function (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};
    
    //Declare local instance variables
    let cfg = global.population_Stadester_config;
    let cleaned_folder = options.ghs_pop_cleaned_folder || (cfg && cfg.ghs_pop_cleaned_folder) ||
      path.join((typeof h2 !== "undefined") ? h2 : "./histmap/2.data_cleaning", "population_GHSL", "cleaned_rasters");
    let land_candidates = [
      options.land_area_raster_path,
      cfg && cfg.land_area_raster_path,
      path.join((typeof h1 !== "undefined") ? h1 : "./histmap/1.data_raw", "metadata_HYDE", "general_rasters", "land_area.png"),
      "./histmap/1.data_raw/metadata_HYDE/general_rasters/land_area.png"
    ];
    let land_data = null;
    let land_path = null;
    let pngjs_lib = (typeof pngjs !== "undefined") ? pngjs : (global.pngjs || require("pngjs"));
    let raw_fallback_folder = options.ghs_pop_raw_fallback_folder || (cfg && cfg.ghs_pop_raw_fallback_folder) ||
      path.join((typeof h1 !== "undefined") ? h1 : "./histmap/1.data_raw", "population_GHSL", "population_rasters", "2.rasters");
    let ref_candidates = [
      path.join(cleaned_folder, "GHS_POP_2020.png"),
      path.join(raw_fallback_folder, "GHS_POP_2020.png")
    ];
    let ref_pop_data = null;
    
    //Function body
    for (let i = 0; i < land_candidates.length; i++) {
      if (land_candidates[i] && fs.existsSync(land_candidates[i])) {
        land_path = land_candidates[i];
        break;
      }
    }
    if (land_path) {
      let land_png = pngjs_lib.PNG.sync.read(fs.readFileSync(land_path));
      let land_dv = new DataView(land_png.data.buffer, land_png.data.byteOffset, land_png.data.byteLength);
      let total_px = land_png.width*land_png.height;
      land_data = new Uint32Array(total_px);
      for (let i = 0; i < total_px; i++)
        land_data[i] = land_dv.getUint32(i*4, false);
    }
    
    for (let i = 0; i < ref_candidates.length; i++) {
      if (ref_candidates[i] && fs.existsSync(ref_candidates[i])) {
        let ref_png = pngjs_lib.PNG.sync.read(fs.readFileSync(ref_candidates[i]));
        let ref_dv = new DataView(ref_png.data.buffer, ref_png.data.byteOffset, ref_png.data.byteLength);
        let total_px = ref_png.width*ref_png.height;
        let y_shift = (i === 1) ? -1 : 0;
        ref_pop_data = new Float32Array(total_px);
        for (let y = 0; y < ref_png.height; y++) {
          let sy = Math.min(ref_png.height - 1, Math.max(0, y + y_shift));
          for (let x = 0; x < ref_png.width; x++) {
            let v = ref_dv.getFloat32((sy*ref_png.width + x)*4, false);
            ref_pop_data[y*ref_png.width + x] = (Number.isFinite(v) && v > 0) ? v : 0;
          }
        }
        break;
      }
    }
    
    //Return statement
    return { land_data: land_data, ref_pop_data: ref_pop_data };
  };
  
  /**
   * Dynamically partitions 5-arcmin GHS-POP gridcells evenly (1/N) across active Stadestér settlements missing a GHS-UCDB entry,
   * strictly for post-empirical years (yr > _raw_max_year), whilst leaving empirical, inter-empirical, manual and war-displacement years intact.
   * @alias population_Stadester_ghs_pop.partitionGHSPopGridcells
   * 
   * @param {Object} arg0_stadester_obj
   * @param {Array<Object>} arg1_city_entries
   * @param {Object} [arg2_options]
   * 
   * @returns {Object}
   */
  population_Stadester_ghs_pop.partitionGHSPopGridcells = function (arg0_stadester_obj, arg1_city_entries, arg2_options) {
    //Convert from parameters
    let stadester_obj = arg0_stadester_obj;
    let city_entries = Array.isArray(arg1_city_entries) ? arg1_city_entries : [];
    let options = (arg2_options) ? arg2_options : {};
    
    //Declare local instance variables
    let bridged_count = 0;
    let cell_map = new Map();
    let cfg = global.population_Stadester_config;
    let cleaned_2020_plus_y_offset = (cfg && cfg.cleaned_2020_plus_y_offset !== undefined) ? cfg.cleaned_2020_plus_y_offset : 0;
    let cleaned_folder = options.ghs_pop_cleaned_folder || (cfg && cfg.ghs_pop_cleaned_folder) ||
      path.join((typeof h2 !== "undefined") ? h2 : "./histmap/2.data_cleaning", "population_GHSL", "cleaned_rasters");
    let cleaned_pre_2020_y_offset = (cfg && cfg.cleaned_pre_2020_y_offset !== undefined) ? cfg.cleaned_pre_2020_y_offset : -1;
    let cutoff_year = (options.cutoff_year !== undefined) ? options.cutoff_year : ((cfg && cfg.cutoff_year !== undefined) ? cfg.cutoff_year : 1975);
    let end_year = (options.end_year !== undefined) ? options.end_year : ((cfg && cfg.end_year !== undefined) ? cfg.end_year : 2025);
    let hyde_years = (typeof landuse_HYDE !== "undefined" && Array.isArray(landuse_HYDE.sorted_hyde_years)) ?
      landuse_HYDE.sorted_hyde_years : population_Stadester_uud.getDefaultHYDEYears();
    let land_ref;
    let partitioned_set = new Set();
    let pngjs_lib = (typeof pngjs !== "undefined") ? pngjs : (global.pngjs || require("pngjs"));
    let preserve_manual = (cfg && cfg.preserve_manual_entries !== undefined) ? cfg.preserve_manual_entries : true;
    let preserve_war = (cfg && cfg.preserve_war_displacement_entries !== undefined) ? cfg.preserve_war_displacement_entries : true;
    let raw_fallback_folder = options.ghs_pop_raw_fallback_folder || (cfg && cfg.ghs_pop_raw_fallback_folder) ||
      path.join((typeof h1 !== "undefined") ? h1 : "./histmap/1.data_raw", "population_GHSL", "population_rasters", "2.rasters");
    let raw_fallback_y_offset = (cfg && cfg.raw_fallback_y_offset !== undefined) ? cfg.raw_fallback_y_offset : -1;
    let spatial_grid = new Map();
    
    //Guard clauses
    if (!stadester_obj || city_entries.length === 0) return stadester_obj;
    
    //1. Suppress co-located non-UCDB agglomeration twins past their empirical span so one town never receives double shares
    for (let i = 0; i < city_entries.length; i++) {
      let ce = city_entries[i];
      let gk = `${Math.floor(ce.lng)},${Math.floor(ce.lat)}`;
      if (!spatial_grid.has(gk)) spatial_grid.set(gk, []);
      spatial_grid.get(gk).push(ce);
    }
    
    for (let i = 0; i < city_entries.length; i++) {
      let ce = city_entries[i];
      if (ce.has_ucdb || ce.is_suppressed_ucdb_twin) continue;
      let lower_key = String(ce.key || "").toLowerCase();
      let is_agg = lower_key.includes("agglomeration") || lower_key.includes("greater") || Boolean(ce.city.is_agglomeration_of);
      if (!is_agg) continue;
      
      let glat = Math.floor(ce.lat);
      let glng = Math.floor(ce.lng);
      let has_core_twin = false;
      for (let dx = -1; dx <= 1 && !has_core_twin; dx++) {
        for (let dy = -1; dy <= 1 && !has_core_twin; dy++) {
          let peers = spatial_grid.get(`${glng + dx},${glat + dy}`);
          if (!peers) continue;
          for (let a = 0; a < peers.length; a++) {
            let peer = peers[a];
            if (peer === ce || peer.is_suppressed_ucdb_twin) continue;
            let p_lower = String(peer.key || "").toLowerCase();
            if (p_lower.includes("agglomeration") || p_lower.includes("greater")) continue;
            let dist_km = population_Stadester_uud.haversineDistance(ce.city.coords, peer.city.coords);
            if (dist_km <= 25 && population_Stadester_ghsl.isCoLocatedCityTwin(ce, peer, dist_km)) {
              has_core_twin = true;
              break;
            }
          }
        }
      }
      if (has_core_twin) {
        ce.is_suppressed_non_ucdb_twin = true;
        if (ce.city.population) {
          let start_zero = Number.isFinite(ce.raw_max_year) ? Math.max(cutoff_year, ce.raw_max_year + 1) : cutoff_year;
          for (let yr = start_zero; yr <= end_year; yr++)
            ce.city.population[yr] = 0;
        }
      }
    }
    
    //2. Snap coastal water zero-cells and bin active settlements per effective gridcell
    land_ref = population_Stadester_ghs_pop.loadLandAndReferenceRasters(options);
    for (let i = 0; i < city_entries.length; i++) {
      let ce = city_entries[i];
      if (ce.is_suppressed_ucdb_twin || ce.is_suppressed_non_ucdb_twin) continue;
      let eff = population_Stadester_ghs_pop.resolveEffectiveGridcell(ce.px, ce.py, land_ref.land_data, land_ref.ref_pop_data, options);
      ce.eff_px = eff[0];
      ce.eff_py = eff[1];
      let cell_key = `${eff[0]},${eff[1]}`;
      if (!cell_map.has(cell_key)) cell_map.set(cell_key, []);
      cell_map.get(cell_key).push(ce);
    }
    
    //3. Stream annual GHS_POP rasters (1975-2025) and split gridcell population across active settlements for post-empirical tails
    for (let yr = cutoff_year; yr <= end_year; yr++) {
      let cleaned_path = path.join(cleaned_folder, `GHS_POP_${yr}.png`);
      let fallback_path = path.join(raw_fallback_folder, `GHS_POP_${yr}.png`);
      let raster_path = null;
      let y_offset = 0;
      
      if (fs.existsSync(cleaned_path)) {
        raster_path = cleaned_path;
        y_offset = (yr < 2020) ? cleaned_pre_2020_y_offset : cleaned_2020_plus_y_offset;
      } else if (fs.existsSync(fallback_path)) {
        raster_path = fallback_path;
        y_offset = raw_fallback_y_offset;
      }
      if (!raster_path) continue;
      
      let png_obj = pngjs_lib.PNG.sync.read(fs.readFileSync(raster_path));
      let dv = new DataView(png_obj.data.buffer, png_obj.data.byteOffset, png_obj.data.byteLength);
      
      for (let cell_entry of cell_map.entries()) {
        let members = cell_entry[1];
        let active_members = [];
        let fallback_targets = [];
        let ramp_targets = [];
        
        for (let i = 0; i < members.length; i++) {
          let m = members[i];
          if (Number.isFinite(m.found_yr) && yr < m.found_yr && !(m.raw_pop && Number(m.raw_pop[yr]) > 0))
            continue;
          active_members.push(m);
        }
        if (active_members.length === 0) continue;
        
        for (let i = 0; i < active_members.length; i++) {
          let m = active_members[i];
          if (preserve_manual && m.city.type === "manual") continue;
          if (preserve_war && m.war_years_set && m.war_years_set.has(yr)) continue;
          if (!Number.isFinite(m.raw_max_year) || !(yr > m.raw_max_year)) continue;
          
          let ucdb_w = (m.ucdb_weight_by_year && m.ucdb_weight_by_year[yr] !== undefined) ?
            m.ucdb_weight_by_year[yr] : 0;
          if (ucdb_w >= 1 - 1e-9) continue;
          if (ucdb_w > 0) {
            ramp_targets.push({ ce: m, ucdb_pop: m.ucdb_pop_by_year[yr] || 0, weight: ucdb_w });
          } else {
            fallback_targets.push(m);
          }
        }
        
        if (fallback_targets.length === 0 && ramp_targets.length === 0) continue;
        
        let eff_px = active_members[0].eff_px;
        let sample_py = Math.min(png_obj.height - 1, Math.max(0, active_members[0].eff_py + y_offset));
        let raw_val = dv.getFloat32((sample_py*png_obj.width + eff_px)*4, false);
        let cell_pop = (Number.isFinite(raw_val) && raw_val > 0) ? raw_val : 0;
        let n_active = active_members.length;
        
        if (fallback_targets.length > 0) {
          let alloc_map = population_Stadester_ghs_pop.distributeCellShare(cell_pop, n_active, fallback_targets);
          for (let i = 0; i < fallback_targets.length; i++) {
            let target_ce = fallback_targets[i];
            if (!target_ce.city.population) target_ce.city.population = {};
            target_ce.city.population[yr] = alloc_map.get(target_ce);
            partitioned_set.add(target_ce.key);
          }
        }
        
        for (let i = 0; i < ramp_targets.length; i++) {
          let rt = ramp_targets[i];
          let even_share = cell_pop/n_active;
          if (!rt.ce.city.population) rt.ce.city.population = {};
          rt.ce.city.population[yr] = Math.max(0, Math.round((1 - rt.weight)*even_share + rt.weight*rt.ucdb_pop));
          partitioned_set.add(rt.ce.key);
        }
      }
    }
    
    //4. Linearly bridge pre-cutoff post-empirical spans (_raw_max_year .. 1975) for earlier-dated cities
    for (let i = 0; i < city_entries.length; i++) {
      let ce = city_entries[i];
      if (ce.is_suppressed_ucdb_twin || ce.is_suppressed_non_ucdb_twin) continue;
      if (!Number.isFinite(ce.raw_max_year) || ce.raw_max_year >= cutoff_year) continue;
      if (!ce.city.population || ce.city.population[cutoff_year] === undefined) continue;
      
      let gap = cutoff_year - ce.raw_max_year;
      let max_gap = (typeof population_Stadester_uud !== "undefined" && typeof population_Stadester_uud.getMaxTemporalProximityGap === "function") ?
        population_Stadester_uud.getMaxTemporalProximityGap(ce.raw_max_year, cutoff_year) : 200;
      if (gap > 1 && gap <= max_gap) {
        let v0 = Number(ce.city.population[ce.raw_max_year]) || 0;
        let v1 = Number(ce.city.population[cutoff_year]) || 0;
        let did_bridge = false;
        for (let x = 0; x < hyde_years.length; x++) {
          let hy = hyde_years[x];
          if (hy > ce.raw_max_year && hy < cutoff_year && ce.city.population[hy] === undefined) {
            ce.city.population[hy] = Math.max(0, Math.round(v0 + ((hy - ce.raw_max_year)/gap)*(v1 - v0)));
            did_bridge = true;
          }
        }
        if (did_bridge) bridged_count++;
      }
    }
    
    console.log(`- Partitioned post-empirical GHS-POP gridcells (1975-2025) for ${partitioned_set.size} settlements (${bridged_count} pre-1975 bridges).`);
    
    //Return statement
    return stadester_obj;
  };
  
  /**
   * Resolves the effective 5-arcmin gridcell [px, py], snapping offshore zero-cells to the nearest populated land pixel within radius.
   * @alias population_Stadester_ghs_pop.resolveEffectiveGridcell
   * 
   * @param {number} arg0_px
   * @param {number} arg1_py
   * @param {Uint32Array|null} arg2_land_data
   * @param {Float32Array|null} arg3_ref_pop_data
   * @param {Object} [arg4_options]
   * 
   * @returns {Array<number>}
   */
  population_Stadester_ghs_pop.resolveEffectiveGridcell = function (arg0_px, arg1_py, arg2_land_data, arg3_ref_pop_data, arg4_options) {
    //Convert from parameters
    let px = parseInt(arg0_px);
    let py = parseInt(arg1_py);
    let land_data = arg2_land_data;
    let ref_pop_data = arg3_ref_pop_data;
    let options = (arg4_options) ? arg4_options : {};
    
    //Declare local instance variables
    let best_dist = Infinity;
    let best_nx = px;
    let best_ny = py;
    let best_pop = 0;
    let cfg = global.population_Stadester_config;
    let height = options.height || 2160;
    let idx = py*4320 + px;
    let radius = (options.coastal_snap_radius_px !== undefined) ?
      options.coastal_snap_radius_px : ((cfg && cfg.coastal_snap_radius_px !== undefined) ? cfg.coastal_snap_radius_px : 1);
    let width = options.width || 4320;
    
    //Guard clauses
    if (!land_data || !ref_pop_data || radius <= 0) return [px, py];
    if (land_data[idx] > 0 || ref_pop_data[idx] > 0) return [px, py];
    
    //Function body
    for (let y = -radius; y <= radius; y++) {
      let ny = py + y;
      if (ny < 0 || ny >= height) continue;
      for (let x = -radius; x <= radius; x++) {
        if (x === 0 && y === 0) continue;
        let nx = ((px + x) % width + width) % width;
        let n_idx = ny*width + nx;
        let n_pop = ref_pop_data[n_idx];
        if (n_pop <= 0) continue;
        
        let dist = Math.abs(x) + Math.abs(y);
        let land_bonus = (land_data[n_idx] > 0) ? 0 : 0.5;
        let eff_dist = dist + land_bonus;
        if (eff_dist < best_dist || (eff_dist === best_dist && n_pop > best_pop)) {
          best_dist = eff_dist;
          best_nx = nx;
          best_ny = ny;
          best_pop = n_pop;
        }
      }
    }
    
    //Return statement
    return [best_nx, best_ny];
  };
  
  /**
   * Restores curated manual city trajectories (type === "manual") when preserve_manual_entries is enabled.
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
      if (ce.city && ce.city.type === "manual" && ce.manual_pop_backup) {
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
  
  global.population_Stadester_ghs_pop_loaded = true;
}
