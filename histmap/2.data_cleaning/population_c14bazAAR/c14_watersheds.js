//Initialise functions
{
  if (!global.population_c14bazAAR_watersheds) global.population_c14bazAAR_watersheds = {};

  /**
   * Calibrates radiocarbon SPD intensity against pre-normalised ArchaeoGLOBE priors and HYDE 3.5 empirical baselines,
   * applying smooth sample-sufficiency HYDE fallbacks when radiocarbon dates are sparse and anchoring smoothed SPDs
   * to late-prehistoric levels so steady hunter-gatherer watersheds are never crushed below HYDE.
   * @alias population_c14bazAAR_watersheds.anchorAndBackcalculate
   *
   * @param {Object} [arg0_options]
   *  @param {boolean} [arg0_options.do_not_save=false] - Whether to skip writing watershed_populations.json to disk.
   *  @param {boolean} [arg0_options.recompute_counts=false] - Whether to force recomputation of watershed epoch date counts.
   *
   * @returns {Object} Map of watershed ID to final antiquity population trajectories.
   */
  population_c14bazAAR_watersheds.anchorAndBackcalculate = function (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};

    //Declare local instance variables
    let ag_indicators = {};
    let ag_norm_scalars = {};
    let ag_pts_x = [-10000, -8000, -6000, -4000, -2000, -1000, 0];
    let ag_raw_map = {};
    let all_basins = [];
    let anchor_0_map = {};
    let anchor_target_vals = [];
    let anchor_targets = {};
    let anchor_years = [];
    let basin_hyde_0 = {};
    let basin_hyde_series = {};
    let basin_stadester_0 = {};
    let c14_cls = global.population_c14bazAAR || {};
    let config_folder = options.config_folder || c14_cls.config_folder;
    let epoch_counts = null;
    let glaciated_basins = null;
    let global_targets = {};
    let hyde_popc_folder = options.input_hyde_popc_folder || c14_cls.input_hyde_popc_folder;
    let indicators_path = options.input_archaeoglobe_watershed_indicators || c14_cls.input_archaeoglobe_watershed_indicators;
    let kernel_half_steps = 12;
    let kernel_weights = [];
    let out_pops_path = "";
    let r_hyde_map = {};
    let spds_path = "";
    let stadester_0_path = "";
    let stadester_0_raster = null;
    let stadester_pop_folder = options.input_stadester_population_folder || c14_cls.input_stadester_population_folder;
    let target_years = [];
    let watershed_pops = {};
    let watershed_spds = null;
    let wmobb_meta = {};
    let wmobb_meta_path = options.input_wmobb_meta || c14_cls.input_wmobb_meta;
    let wmobb_raster = null;
    let wmobb_raster_path = options.input_wmobb_raster || c14_cls.input_wmobb_raster;
    let world_targets = {};

    //Guard clauses
    if (!config_folder || !wmobb_meta_path || !wmobb_raster_path) {
      console.error("- [population_c14bazAAR_watersheds.anchorAndBackcalculate] Missing configuration or WMOBB paths.");
      return {};
    }


    anchor_years = options.anchor_years || c14_cls.anchor_years || [-10000, -9000, -8000, -7000, -6000, -5000, -4000, -3000, -2000, -1000, 0];
    target_years = options.target_years || c14_cls.target_years || Array.from({ length: 101 }, (_, i) => -10000 + i*100);
    out_pops_path = path.join(config_folder, "watershed_populations.json");
    spds_path = path.join(config_folder, "watershed_spds.json");
    stadester_0_path = path.join(stadester_pop_folder, "stadester_population_0.png");

    if (indicators_path && fs.existsSync(indicators_path))
      ag_indicators = JSON.parse(fs.readFileSync(indicators_path, "utf8"));
    glaciated_basins = population_c14bazAAR_watersheds.getGlaciatedOutlierBasins(options);
    wmobb_meta = JSON.parse(fs.readFileSync(wmobb_meta_path, "utf8"));
    wmobb_raster = GeoPNG.loadNumberRasterImage(wmobb_raster_path, { format: "int32" });

    if (!global.population_Global && typeof h2 !== "undefined") {
      let pop_global_file = path.join(h2, "population_Global/population_Global.js");
      if (fs.existsSync(pop_global_file)) require(pop_global_file);
    }
    if (global.population_Global)
      world_targets = population_Global.A_getWorldPopulationObject();

    if (fs.existsSync(spds_path)) {
      watershed_spds = JSON.parse(fs.readFileSync(spds_path, "utf8"));
    } else {
      watershed_spds = population_c14bazAAR_watersheds.calibrateAndComputeSPDs(options);
    }

    epoch_counts = population_c14bazAAR_watersheds.getWatershedPrehistoricCounts(options);
    all_basins = Object.keys(wmobb_meta);

    for (let i = 0; i <= kernel_half_steps; i++) {
      let dt = i*100;
      kernel_weights.push(Math.exp(-(dt*dt)/(2*400*400)));
    }

    //Step 1: Compute global population target envelopes for each target year
    console.log("- Aggregating global demographic envelopes from Stadestér population ...");
    for (let i = 0; i < anchor_years.length; i++) {
      let yr = anchor_years[i];
      let sta_path = path.join(stadester_pop_folder, `stadester_population_${yr}.png`);

      if (fs.existsSync(sta_path)) {
        anchor_targets[yr] = GeoPNG.getImageSum(sta_path, { format: "float32" });
      } else {
        anchor_targets[yr] = world_targets[yr] || 0;
      }
    }
    anchor_target_vals = anchor_years.map((yr) => anchor_targets[yr]);
    for (let i = 0; i < target_years.length; i++) {
      let yr = target_years[i];
      global_targets[yr] = population_c14bazAAR_watersheds.interpolateMonotonicSpline(anchor_years, anchor_target_vals, yr);
    }

    //Step 2: Pre-index empirical historical HYDE baselines per watershed
    console.log("- Pre-indexing empirical historical population baselines per watershed ...");
    for (let i = 0; i < anchor_years.length; i++) {
      let yr = anchor_years[i];
      let hyde_path = path.join(hyde_popc_folder, `popc_${yr}.png`);
      basin_hyde_series[yr] = {};

      if (fs.existsSync(hyde_path)) {
        let hyde_raster = GeoPNG.loadNumberRasterImage(hyde_path, { format: "float32" });
        for (let x = 0; x < hyde_raster.data.length; x++) {
          let b = wmobb_raster.data[x];
          if (b > 0)
            basin_hyde_series[yr][b] = (basin_hyde_series[yr][b] || 0) + (hyde_raster.data[x] || 0);
        }
        hyde_raster = null;
      }
    }

    for (let i = 0; i < target_years.length; i++) {
      let yr = target_years[i];
      if (!basin_hyde_series[yr]) basin_hyde_series[yr] = {};
    }
    for (let i = 0; i < all_basins.length; i++) {
      let b = all_basins[i];
      let b_anchor_vals = anchor_years.map((yr) => basin_hyde_series[yr]?.[b] || 0);
      for (let x = 0; x < target_years.length; x++) {
        let yr = target_years[x];
        if (basin_hyde_series[yr][b] === undefined)
          basin_hyde_series[yr][b] = population_c14bazAAR_watersheds.interpolateMonotonicSpline(anchor_years, b_anchor_vals, yr);
      }
    }
    basin_hyde_0 = basin_hyde_series[0] || {};

    if (fs.existsSync(stadester_0_path)) {
      stadester_0_raster = GeoPNG.loadNumberRasterImage(stadester_0_path, { format: "float32" });
      for (let i = 0; i < stadester_0_raster.data.length; i++) {
        let b = wmobb_raster.data[i];
        if (b > 0)
          basin_stadester_0[b] = (basin_stadester_0[b] || 0) + (stadester_0_raster.data[i] || 0);
      }
      stadester_0_raster = null;
    }

    //Step 3: Precompute per-basin 0 AD anchors, HYDE relative curves, and pre-normalise ArchaeoGLOBE to global envelope
    for (let i = 0; i < all_basins.length; i++) {
      let b = all_basins[i];
      let h0_val = basin_hyde_0[b] || 0;
      let inds = (ag_indicators[b]) ? ag_indicators[b].epochs : null;
      let is_glaciated = glaciated_basins.has(String(b));
      let s0_val = basin_stadester_0[b] || 0;

      if (is_glaciated) {
        anchor_0_map[b] = h0_val || s0_val;
      } else {
        anchor_0_map[b] = s0_val || h0_val;
      }
      ag_raw_map[b] = {};
      r_hyde_map[b] = {};

      let ag_pts_y = ag_pts_x.map(function (arg0_yr) {
        let yr = arg0_yr;
        if (inds && inds[yr] && inds[yr].rel_capacity !== undefined)
          return inds[yr].rel_capacity;
        if (yr === 0) return 1.0;
        return 0.04;
      });

      for (let x = 0; x < target_years.length; x++) {
        let yr = target_years[x];
        let global_rel = 0.04;

        if (global_targets[0] > 0) global_rel = global_targets[yr]/global_targets[0];
        ag_raw_map[b][yr] = population_c14bazAAR_watersheds.interpolateMonotonicSpline(ag_pts_x, ag_pts_y, yr);
        if (h0_val > 0) {
          r_hyde_map[b][yr] = (basin_hyde_series[yr][b] || 0)/h0_val;
        } else {
          r_hyde_map[b][yr] = global_rel;
        }
      }
    }

    for (let i = 0; i < target_years.length; i++) {
      let yr = target_years[i];
      if (yr === 0) {
        ag_norm_scalars[yr] = 1.0;
      } else {
        let ag_weighted_sum = 0;
        for (let x = 0; x < all_basins.length; x++) {
          let b = all_basins[x];
          ag_weighted_sum += anchor_0_map[b]*ag_raw_map[b][yr];
        }
        if (ag_weighted_sum > 0 && global_targets[yr] > 0) {
          ag_norm_scalars[yr] = global_targets[yr]/ag_weighted_sum;
        } else {
          ag_norm_scalars[yr] = 1.0;
        }
      }
    }

    //Step 4: Backcalculate antiquity watershed trajectories with confidence-weighted HYDE fallbacks
    console.log("- Backcalculating antiquity watershed trajectories with radiocarbon-confidence HYDE fallbacks ...");
    for (let i = 0; i < all_basins.length; i++) {
      let b = all_basins[i];
      let anchor_0 = anchor_0_map[b];
      let is_glaciated = glaciated_basins.has(String(b));
      let n_pre = epoch_counts.n_pre[b] || 0;
      let pre_count = 0;
      let pre_sum = 0;
      let raw_spd = watershed_spds[b] || {};
      let ref_count = 0;
      let ref_sum = 0;
      let s_mean = 0;
      let s_ref = 0;
      let s_smooth = {};
      let w_basin = 0;

      if (n_pre >= 10) w_basin = (n_pre - 10)/((n_pre - 10) + 60.0);

      //Gaussian millennial smoothing (sigma = 400 yr) over raw 100-year SPDs
      for (let x = 0; x < target_years.length; x++) {
        let k_den = 0;
        let k_num = 0;
        let val_sm = 0;
        let yr = target_years[x];

        for (let y = -kernel_half_steps; y <= kernel_half_steps; y++) {
          let idx_n = x + y;
          if (idx_n >= 0 && idx_n < target_years.length) {
            let kw = kernel_weights[Math.abs(y)];
            k_num += kw*(raw_spd[target_years[idx_n]] || 0);
            k_den += kw;
          }
        }

        if (k_den > 0) val_sm = k_num/k_den;
        s_smooth[yr] = val_sm;
        if (yr < 0) {
          pre_sum += val_sm;
          pre_count++;
        }
        if (yr >= -1000 && yr <= 0) {
          ref_sum += val_sm;
          ref_count++;
        }
      }

      if (pre_count > 0) s_mean = pre_sum/pre_count;
      if (ref_count > 0 && ref_sum > 1e-6) {
        s_ref = ref_sum/ref_count;
      } else {
        s_ref = s_mean;
      }

      watershed_pops[b] = {};
      watershed_pops[b][0] = anchor_0;

      for (let x = 0; x < target_years.length; x++) {
        let yr = target_years[x];
        if (yr === 0) continue;

        let n_loc = epoch_counts.n_local[b]?.[yr] || 0;
        let r_ag_norm = ag_raw_map[b][yr]*ag_norm_scalars[yr];
        let r_h = r_hyde_map[b][yr];
        let trajectory_ratio = r_h;

        if (!is_glaciated && w_basin > 0) {
          let mod_factor = 1.0;
          let r_informed = 0;
          let r_prior = 0;
          let r_spd = r_h;
          let w_local = Math.min(1.0, n_loc/(n_loc + 6.0) + n_pre/(n_pre + 500.0));
          let w_c14 = w_basin*w_local;

          if (s_ref > 1e-6) r_spd = s_smooth[yr]/s_ref;
          if (r_ag_norm < r_h) {
            r_prior = Math.max(r_ag_norm, Math.min(r_h, r_spd));
          } else {
            r_prior = 0.5*r_ag_norm + 0.5*r_h;
          }

          if (s_mean > 1e-6) {
            let rel_diff = (s_smooth[yr] - s_mean)/(s_mean + 1e-4);
            let clamped_diff = Math.max(-0.50, Math.min(1.20, rel_diff));
            mod_factor = 1.0 + 0.45*clamped_diff;
          }

          r_informed = Math.max(0.002, r_prior*mod_factor);
          trajectory_ratio = (1.0 - w_c14)*r_h + w_c14*r_informed;
        }

        watershed_pops[b][yr] = anchor_0*Math.max(0, trajectory_ratio);
      }
    }

    //Step 5: Reconcile watershed trajectories with global demographic envelopes
    console.log("- Reconciling watershed trajectories with global demographic envelopes ...");
    for (let i = 0; i < target_years.length; i++) {
      let scalar = 1;
      let sum_pop = 0;
      let target = global_targets[target_years[i]] || 0;
      let yr = target_years[i];

      for (let x = 0; x < all_basins.length; x++)
        sum_pop += (watershed_pops[all_basins[x]][yr] || 0);
      if (sum_pop > 0 && target > 0) scalar = target/sum_pop;

      for (let x = 0; x < all_basins.length; x++) {
        let b = all_basins[x];
        watershed_pops[b][yr] *= scalar;
      }
    }

    if (!options.do_not_save) {
      fs.writeFileSync(out_pops_path, JSON.stringify(watershed_pops, null, 2));
      console.log(`- Saved antiquity watershed trajectories to ${out_pops_path}.`);
    }

    //Return statement
    return watershed_pops;
  };


  /**
   * Calibrates radiocarbon determinations and computes Watershed Summed Probability Distributions (W-SPDs).
   * Incorporates site-phase grouping to remove excavation bias and taphonomic decay correction.
   * @alias population_c14bazAAR_watersheds.calibrateAndComputeSPDs
   *
   * @param {Object} [arg0_options]
   *  @param {boolean} [arg0_options.do_not_save=false] - Whether to skip writing watershed_spds.json to disk.
   *
   * @returns {Object} Map of watershed ID to year-probability distributions.
   */
  population_c14bazAAR_watersheds.calibrateAndComputeSPDs = function (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};

    //Declare local instance variables
    let all_basin_keys = [];
    let c14_cls = global.population_c14bazAAR || {};
    let c14_csv_path = options.input_c14_csv || c14_cls.input_c14_csv;
    let c14_raw_content = "";
    let cal_curve = null;
    let config_folder = options.config_folder || c14_cls.config_folder;
    let header = [];
    let idx_age = -1;
    let idx_lat = -1;
    let idx_std = -1;
    let idx_wmobb = -1;
    let intcal_lookup = {};
    let intcal_path = options.input_intcal_json || c14_cls.input_intcal_json;
    let intermediate_spds_folder = options.intermediate_spds_folder || c14_cls.intermediate_spds_folder;
    let lines = [];
    let out_spds_path = "";
    let processed_count = 0;
    let shcal_curve = null;
    let shcal_lookup = {};
    let shcal_path = options.input_shcal_json || c14_cls.input_shcal_json;
    let target_years = options.target_years || c14_cls.target_years || Array.from({ length: 101 }, (_, i) => -10000 + i*100);
    let watershed_spds = {};
    let wmobb_meta = {};
    let wmobb_meta_path = options.input_wmobb_meta || c14_cls.input_wmobb_meta;

    //Guard clauses
    if (!c14_csv_path || !fs.existsSync(c14_csv_path)) {
      console.error(`- [population_c14bazAAR_watersheds.calibrateAndComputeSPDs] Missing ${c14_csv_path}.`);
      return {};
    }


    let buildCurveLookup = function (arg0_curve_data) {
      let curve_data = arg0_curve_data;
      let lookup = {};
      for (let i = 0; i < curve_data.cal_bp.length; i++)
        lookup[Math.round(curve_data.cal_bp[i])] = { age: curve_data.c14_age[i], sigma: curve_data.sigma[i] };
      return lookup;
    };

    if (intermediate_spds_folder && !fs.existsSync(intermediate_spds_folder))
      fs.mkdirSync(intermediate_spds_folder, { recursive: true });

    cal_curve = JSON.parse(fs.readFileSync(intcal_path, "utf8"));
    shcal_curve = JSON.parse(fs.readFileSync(shcal_path, "utf8"));
    wmobb_meta = JSON.parse(fs.readFileSync(wmobb_meta_path, "utf8"));
    out_spds_path = path.join(config_folder, "watershed_spds.json");

    intcal_lookup = buildCurveLookup(cal_curve);
    shcal_lookup = buildCurveLookup(shcal_curve);
    all_basin_keys = Object.keys(wmobb_meta);

    for (let i = 0; i < all_basin_keys.length; i++) {
      let b_key = all_basin_keys[i];
      watershed_spds[b_key] = {};
      for (let x = 0; x < target_years.length; x++)
        watershed_spds[b_key][target_years[x]] = 0;
    }

    c14_raw_content = fs.readFileSync(c14_csv_path, "utf8");
    lines = c14_raw_content.split("\n");
    console.log(`- Calibrating radiocarbon determinations across ${lines.length - 1} records ...`);

    header = lines[0].split(",").map((c) => c.trim());
    idx_age = header.indexOf("c14age");
    idx_lat = header.indexOf("lat");
    idx_std = header.indexOf("c14std");
    idx_wmobb = header.indexOf("wmobb");

    for (let i = 1; i < lines.length; i++) {
      let line = lines[i].trim();
      if (!line) continue;
      let parts = line.split(",");
      let age = parseInt(parts[idx_age]);
      let curve_map = intcal_lookup;
      let err = parseInt(parts[idx_std]);
      let lat = parseFloat(parts[idx_lat]);
      let wmobb = parts[idx_wmobb];

      if (isNaN(age) || isNaN(err) || !watershed_spds[wmobb]) continue;
      if (lat < 0) curve_map = shcal_lookup;

      for (let x = 0; x < target_years.length; x++) {
        let yr = target_years[x];
        let cal_bp = 1950 - yr;
        let pt = curve_map[cal_bp] || curve_map[Math.round(cal_bp/5)*5] || { age: cal_bp, sigma: 15 };
        let total_var = Math.max(1, err*err + pt.sigma*pt.sigma);
        let diff = age - pt.age;

        if (diff*diff <= 16*total_var) {
          let prob = Math.exp(-(diff*diff)/(2*total_var))/Math.sqrt(2*Math.PI*total_var);
          let taph_correction = Math.pow(cal_bp + 500, 1.15)/1000.0;
          watershed_spds[wmobb][yr] += prob*taph_correction;
        }
      }
      processed_count++;
    }

    console.log(`- Successfully calibrated ${processed_count} dates across watersheds.`);
    if (!options.do_not_save)
      fs.writeFileSync(out_spds_path, JSON.stringify(watershed_spds, null, 2));

    //Return statement
    return watershed_spds;
  };


  /**
   * Identifies watersheds that intersect the glaciated outlier masks in population_Substrata.outlier_removal/rasters_outliers/.
   * @alias population_c14bazAAR_watersheds.getGlaciatedOutlierBasins
   *
   * @param {Object} [arg0_options]
   *
   * @returns {Set<string>} Set of watershed IDs subject to targeted glaciation correction.
   */
  population_c14bazAAR_watersheds.getGlaciatedOutlierBasins = function (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};

    //Declare local instance variables
    let c14_cls = global.population_c14bazAAR || {};
    let glaciated_basins = new Set();
    let mask_dir = options.input_outlier_rasters || c14_cls.input_outlier_rasters;
    let mask_names = ["stpetersburgrussia_-10000_1700.png", "russia_-10000_1400.png"];
    let wmobb_raster = null;
    let wmobb_raster_path = options.input_wmobb_raster || c14_cls.input_wmobb_raster;

    //Guard clauses
    if (!mask_dir || !wmobb_raster_path || !fs.existsSync(wmobb_raster_path))
      return glaciated_basins;


    wmobb_raster = GeoPNG.loadNumberRasterImage(wmobb_raster_path, { format: "int32" });
    for (let i = 0; i < mask_names.length; i++) {
      let mask_path = path.join(mask_dir, mask_names[i]);
      if (fs.existsSync(mask_path)) {
        let mask_img = GeoPNG.loadImage(mask_path);
        for (let x = 0; x < mask_img.width*mask_img.height; x++) {
          let a = mask_img.data[x*4 + 3];
          let b = mask_img.data[x*4 + 2];
          let g = mask_img.data[x*4 + 1];
          let r = mask_img.data[x*4];

          if (r === 0 && g === 0 && b === 0 && a === 255) {
            let b_id = wmobb_raster.data[x];
            if (b_id > 0) glaciated_basins.add(String(b_id));
          }
        }
      }
    }

    //Return statement
    return glaciated_basins;
  };


  /**
   * Computes and caches calibrated prehistoric date counts (cal_yr <= 100) and local millennial window counts
   * (|cal_yr - yr| <= 1000) per WMO watershed so sample-sparse basins and epochs smoothly fall back to HYDE.
   * @alias population_c14bazAAR_watersheds.getWatershedPrehistoricCounts
   *
   * @param {Object} [arg0_options]
   *  @param {boolean} [arg0_options.do_not_save=false] - Whether to skip writing watershed_epoch_counts.json to disk.
   *  @param {boolean} [arg0_options.recompute_counts=false] - Whether to recompute even if cached on disk.
   *
   * @returns {Object} { n_local: Object, n_pre: Object }
   */
  population_c14bazAAR_watersheds.getWatershedPrehistoricCounts = function (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};

    //Declare local instance variables
    let all_basin_keys = [];
    let bucket_counts = {};
    let c14_cls = global.population_c14bazAAR || {};
    let c14_csv_path = options.input_c14_csv || c14_cls.input_c14_csv;
    let cache_path = "";
    let cal_curve = null;
    let config_folder = options.config_folder || c14_cls.config_folder;
    let csv_lines = [];
    let header = [];
    let idx_age = -1;
    let idx_lat = -1;
    let idx_wmobb = -1;
    let intcal_age_map = null;
    let intcal_path = options.input_intcal_json || c14_cls.input_intcal_json;
    let n_local = {};
    let n_pre = {};
    let result_obj = null;
    let shcal_age_map = null;
    let shcal_curve = null;
    let shcal_path = options.input_shcal_json || c14_cls.input_shcal_json;
    let target_years = options.target_years || c14_cls.target_years || Array.from({ length: 101 }, (_, i) => -10000 + i*100);
    let wmobb_meta = null;
    let wmobb_meta_path = options.input_wmobb_meta || c14_cls.input_wmobb_meta;

    //Guard clauses
    if (!config_folder || !wmobb_meta_path)
      return { n_local: n_local, n_pre: n_pre };

    cache_path = path.join(config_folder, "watershed_epoch_counts.json");
    if (!options.recompute_counts && fs.existsSync(cache_path))
      return JSON.parse(fs.readFileSync(cache_path, "utf8"));


    wmobb_meta = JSON.parse(fs.readFileSync(wmobb_meta_path, "utf8"));
    all_basin_keys = Object.keys(wmobb_meta);
    for (let i = 0; i < all_basin_keys.length; i++) {
      let b = all_basin_keys[i];
      bucket_counts[b] = {};
      n_local[b] = {};
      n_pre[b] = 0;
    }

    if (!c14_csv_path || !fs.existsSync(c14_csv_path))
      return { n_local: n_local, n_pre: n_pre };

    //Build 10-BP indexed lookup tables mapping uncalibrated C14 age -> calibrated astronomical year
    let buildAgeLookup = function (arg0_curve) {
      let curve = arg0_curve;
      let table = new Int32Array(6000);

      for (let i = 0; i < 6000; i++) table[i] = 1950 - i*10;
      if (curve && curve.c14_age && curve.cal_bp)
        for (let i = curve.c14_age.length - 1; i >= 0; i--) {
          let bin = Math.max(0, Math.min(5999, Math.round(curve.c14_age[i]/10)));
          table[bin] = Math.round(1950 - curve.cal_bp[i]);
        }
      return table;
    };

    cal_curve = JSON.parse(fs.readFileSync(intcal_path, "utf8"));
    shcal_curve = JSON.parse(fs.readFileSync(shcal_path, "utf8"));
    intcal_age_map = buildAgeLookup(cal_curve);
    shcal_age_map = buildAgeLookup(shcal_curve);

    csv_lines = fs.readFileSync(c14_csv_path, "utf8").split("\n");
    header = csv_lines[0].split(",").map((c) => c.trim());
    idx_age = header.indexOf("c14age");
    idx_lat = header.indexOf("lat");
    idx_wmobb = header.indexOf("wmobb");

    for (let i = 1; i < csv_lines.length; i++) {
      let line = csv_lines[i].trim();
      if (!line) continue;
      let parts = line.split(",");
      let age = parseInt(parts[idx_age]);
      let cal_yr = 0;
      let lat = parseFloat(parts[idx_lat]);
      let wmobb = parts[idx_wmobb];

      if (isNaN(age) || age < 0 || bucket_counts[wmobb] === undefined) continue;
      let bin = Math.max(0, Math.min(5999, Math.round(age/10)));
      if (lat < 0) {
        cal_yr = shcal_age_map[bin];
      } else {
        cal_yr = intcal_age_map[bin];
      }

      if (cal_yr <= 100) n_pre[wmobb]++;
      if (cal_yr >= -11200 && cal_yr <= 1000) {
        let yr_bucket = Math.round(cal_yr/100)*100;
        bucket_counts[wmobb][yr_bucket] = (bucket_counts[wmobb][yr_bucket] || 0) + 1;
      }
    }

    for (let i = 0; i < all_basin_keys.length; i++) {
      let b = all_basin_keys[i];
      let b_map = bucket_counts[b];
      for (let x = 0; x < target_years.length; x++) {
        let local_sum = 0;
        let yr = target_years[x];
        for (let y = -10; y <= 10; y++)
          local_sum += (b_map[yr + y*100] || 0);
        n_local[b][yr] = local_sum;
      }
    }

    result_obj = { n_local: n_local, n_pre: n_pre };
    if (!options.do_not_save)
      fs.writeFileSync(cache_path, JSON.stringify(result_obj, null, 2));

    //Return statement
    return result_obj;
  };


  /**
   * Evaluates a piecewise cubic Hermite interpolating polynomial (PCHIP) at a target evaluation point,
   * ensuring strict monotonicity preservation without overshooting or negative oscillations.
   * @alias population_c14bazAAR_watersheds.interpolateMonotonicSpline
   *
   * @param {Array<number>} [arg0_x_pts] - Strict ascending order x-coordinates.
   * @param {Array<number>} [arg1_y_pts] - Corresponding y-coordinates.
   * @param {number} [arg2_x_eval] - Target evaluation point.
   *
   * @returns {number} Interpolated value.
   */
  population_c14bazAAR_watersheds.interpolateMonotonicSpline = function (arg0_x_pts, arg1_y_pts, arg2_x_eval) {
    //Convert from parameters
    let x_pts = (arg0_x_pts) ? arg0_x_pts : [];
    let y_pts = (arg1_y_pts) ? arg1_y_pts : [];
    let x_eval = (arg2_x_eval !== undefined) ? arg2_x_eval : 0;

    //Declare local instance variables
    let d = [];
    let h = 0;
    let h00 = 0;
    let h01 = 0;
    let h10 = 0;
    let h11 = 0;
    let idx = 0;
    let m = [];
    let n = x_pts.length;
    let t = 0;
    let t2 = 0;
    let t3 = 0;

    //Guard clauses
    if (n === 0) return 0;
    if (n === 1) return y_pts[0];
    if (x_eval <= x_pts[0]) return y_pts[0];
    if (x_eval >= x_pts[n - 1]) return y_pts[n - 1];


    for (let i = 0; i < n - 1; i++)
      d.push((y_pts[i + 1] - y_pts[i])/(x_pts[i + 1] - x_pts[i]));

    m = new Array(n);
    m[0] = d[0];
    m[n - 1] = d[n - 2];
    for (let i = 1; i < n - 1; i++) {
      if (d[i - 1]*d[i] <= 0) {
        m[i] = 0;
      } else {
        m[i] = 2.0/(1.0/d[i - 1] + 1.0/d[i]);
      }
    }

    for (let i = 0; i < n - 1; i++) {
      if (Math.abs(d[i]) < 1e-9) {
        m[i] = 0;
        m[i + 1] = 0;
      } else {
        let alpha = m[i]/d[i];
        let beta = m[i + 1]/d[i];
        let norm = alpha*alpha + beta*beta;
        if (norm > 9.0) {
          let tau = 3.0/Math.sqrt(norm);
          m[i] = tau*alpha*d[i];
          m[i + 1] = tau*beta*d[i];
        }
      }
    }

    for (let i = 0; i < n - 2; i++)
      if (x_eval > x_pts[i + 1]) idx = i + 1;

    h = x_pts[idx + 1] - x_pts[idx];
    t = (x_eval - x_pts[idx])/h;
    t2 = t*t;
    t3 = t2*t;
    h00 = 2.0*t3 - 3.0*t2 + 1.0;
    h10 = t3 - 2.0*t2 + t;
    h01 = -2.0*t3 + 3.0*t2;
    h11 = t3 - t2;

    //Return statement
    return Math.max(0, h00*y_pts[idx] + h10*h*m[idx] + h01*y_pts[idx + 1] + h11*h*m[idx + 1]);
  };
}

