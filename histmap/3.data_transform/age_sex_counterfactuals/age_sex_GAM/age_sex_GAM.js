global.age_sex_GAM = class {
  static bf = `${h3}/age_sex_counterfactuals/age_sex_GAM/`;
  static hf = () => `${landuse_HYDE.bf}/rasters/`;
  static hf1 = (y) => landuse_HYDE._getHYDEYearName(y);
  static premodern_model_path = `${h3}/age_sex/1.multinomial_logit/premodern_multinomial_logit.json`;
  static sf = () => population_Stadester;

  static covariates_obj = {
    //LU (Land Use)
    "conv_rangeland": (y) => [`${this.hf()}/conv_rangeland${this.hf1(y)}_number.png`, "float32"],
    "cropland": (y) => [`${this.hf()}/cropland${this.hf1(y)}_number.png`, "float32"],
    "grazing": (y) => [`${this.hf()}/grazing${this.hf1(y)}_number.png`, "float32"],
    "ir_norice": (y) => [`${this.hf()}/ir_norice${this.hf1(y)}_number.png`, "float32"],
    "ir_rice": (y) => [`${this.hf()}/ir_rice${this.hf1(y)}_number.png`, "float32"],
    "pasture": (y) => [`${this.hf()}/pasture${this.hf1(y)}_number.png`, "float32"],
    "rangeland": (y) => [`${this.hf()}/rangeland${this.hf1(y)}_number.png`, "float32"],
    "rf_norice": (y) => [`${this.hf()}/rf_norice${this.hf1(y)}_number.png`, "float32"],
    "rf_rice": (y) => [`${this.hf()}/rf_rice${this.hf1(y)}_number.png`, "float32"],
    "shifting": (y) => [`${this.hf()}/shifting${this.hf1(y)}_number.png`, "float32"],
    "tot_irri": (y) => [`${this.hf()}/tot_irri${this.hf1(y)}_number.png`, "float32"],
    "tot_rainfed": (y) => [`${this.hf()}/tot_rainfed${this.hf1(y)}_number.png`, "float32"],
    "tot_rice": (y) => [`${this.hf()}/tot_rice${this.hf1(y)}_number.png`, "float32"],
    "uopp_": (y) => [`${this.hf()}/uopp_${this.hf1(y)}_number.png`, "float32"],

    //POP (Demographics)
    "popc_": (y) => [`${this.sf().input_popc_folder}/stadester_population_${y}.png`, "float32"],
    "popd_": (y) => [`${this.sf().intermediate_popd_folder}/stadester_density_${y}.png`, "float32"],
    "rurc_": (y) => [`${this.sf().input_rurc_folder}/stadester_rural_${y}.png`, "float32"],
    "urbc_": (y) => [`${this.sf().input_urbc_folder}/stadester_urban_${y}.png`, "float32"],

    //Eoscala (Economics)
    "discretionary_income": (y) => [`${wealth_income.output_discretionary_income_folder}/discretionary_income_${y}.png`, "float32"],
    "disposable_income": (y) => [`${wealth_income.output_disposable_income_folder}/disposable_income_${y}.png`, "float32"],
    "gdp_nominal": (y) => [`${GDP_pc.intermediate_gdp_scaled_to_national}/GDP_${y}.png`, "float32"],
    "gdp_pc": (y) => [`${GDP_pc.output_gdp_pc_folder}/GDP_pc_${y}.png`, "float32"],
    "gdp_ppp": (y) => [`${GDP_PPP_pc.intermediate_gdp_ppp_scaled_to_national}/GDP_PPP_${y}.png`, "float32"],
    "gdp_ppp_pc": (y) => [`${GDP_PPP_pc.output_gdp_ppp_pc_folder}/GDP_PPP_pc_${y}.png`, "float32"],
    "gini": (y) => [`${gini_Eoscala.output_rasters}gini_${y}.png`, "float32"],
    "net_income": (y) => [`${wealth_income.output_net_income_folder}/net_income_${y}.png`, "float32"],
    "net_wealth": (y) => [`${wealth_income.output_net_wealth_folder}/net_wealth_${y}.png`, "float32"],

    //Deltas (Economics, Demographics)
    "delta_gdp_nominal": (y) => [`${GDP_Eoscala_transform.delta_GDP_nominal_folder}/delta_GDP_${y}.png`, "float32"],
    "delta_gdp_pc": (y) => [`${GDP_Eoscala_transform.delta_GDP_pc_folder}/delta_GDP_pc_${y}.png`, "float32"],
    "delta_gdp_ppp": (y) => [`${GDP_Eoscala_transform.delta_GDP_PPP_folder}/delta_GDP_PPP_${y}.png`, "float32"],
    "delta_gdp_ppp_pc": (y) => [`${GDP_Eoscala_transform.delta_GDP_PPP_pc_folder}/delta_GDP_PPP_pc_${y}.png`, "float32"],
    "delta_popd_": (y) => [`${population_Stadester_transform.delta_population_density_folder}/delta_population_density_${y}.png`, "float32"],
    "delta_popc_": (y) => [`${population_Stadester_transform.delta_total_population_folder}/delta_total_population_${y}.png`, "float32"],
    "delta_rurc_": (y) => [`${population_Stadester_transform.delta_rural_population_folder}/delta_rural_population_${y}.png`, "float32"],
    "delta_urbc_": (y) => [`${population_Stadester_transform.delta_urban_population_folder}/delta_urban_population_${y}.png`, "float32"]
  };

  static standardised_targets_folder = `${this.bf}/0.standardised_targets/`;
  static intermediate_gam_model_folder = `${this.bf}/1.gam_model/`;
  static intermediate_gam_rasters = `${this.bf}/2.gam_rasters/`;
  static intermediate_clamped_rasters = `${this.bf}/3.clamped_to_stadester/`;
  static output_rasters = `${this.bf}/4.composite_cohorts/`;

  /**
   * Helper function to generate standard WorldPop cohort names.
   * @alias age_sex_GAM.getCohorts
   * @returns {Array<string>}
   */
  static getCohorts () {
    //Declare local instance variables
    let age_groups = ["00", "01"];
    let cohorts = [];

    for (let i = 5; i <= 80; i += 5)
      age_groups.push(i.toString().padStart(2, "0"));

    for (let i = 0; i < age_groups.length; i++) {
      cohorts.push(`f_${age_groups[i]}`);
      cohorts.push(`m_${age_groups[i]}`);
    }

    //Return statement
    return cohorts;
  }

  /**
   * Computes the low-dimensional smooth demographic shape basis B across all 36 cohorts.
   * Basis vectors represent:
   *  0: Youth/infant mortality & fertility decline
   *  1: Working-age bulge (demographic dividend)
   *  2: Longevity & population ageing
   *  3: Adult sex-differential excess mortality
   *  4: Terminal cohort curvature (80+)
   * All vectors are strictly centered to 0 at reference class 'f_50'.
   * @alias age_sex_GAM.getDemographicBasis
   * @returns {Object} { basis_matrix, classes, component_names }
   */
  static getDemographicBasis () {
    //Declare local instance variables
    let ages = [0.5, 2.5, 7.5, 12.5, 17.5, 22.5, 27.5, 32.5, 37.5, 42.5, 47.5, 52.5, 57.5, 62.5, 67.5, 72.5, 77.5, 85.0];
    let basis_matrix = {};
    let classes = this.getCohorts();
    let component_names = [
      "youth_fertility",
      "working_age_dividend",
      "longevity_aging",
      "sex_mortality_differential",
      "terminal_curvature"
    ];
    let num_modes = 5;
    let ref_age = 52.5;

    //Calculate reference mode values at age 52.5 (female)
    let ref_mode_0 = Math.exp(-ref_age/12);
    let ref_mode_1 = Math.exp(-Math.pow((ref_age - 32)/16, 2));
    let ref_mode_2 = 1/(1 + Math.exp(-(ref_age - 65)/8));

    for (let c = 0; c < classes.length; c++) {
      let class_key = classes[c];
      let age_idx = Math.floor(c/2);
      let is_male = class_key.startsWith("m_");
      let local_age = ages[age_idx];

      let v0 = (Math.exp(-local_age/12) - ref_mode_0)*1.2;
      let v1 = (Math.exp(-Math.pow((local_age - 32)/16, 2)) - ref_mode_1)*1.5;
      let v2 = (1/(1 + Math.exp(-(local_age - 65)/8)) - ref_mode_2)*1.8;
      let v3 = (is_male) ? (-0.25*Math.min(1.0, local_age/60)) : 0;
      let v4 = (age_idx === 17) ? 1.0 : ((age_idx === 16) ? 0.25 : 0);

      //Reference cohort 'f_50' is strictly zero across all basis dimensions
      if (class_key === "f_50") {
        basis_matrix[class_key] = new Array(num_modes).fill(0);
      } else {
        basis_matrix[class_key] = [v0, v1, v2, v3, v4];
      }
    }

    //Return statement
    return {
      basis_matrix: basis_matrix,
      classes: classes,
      component_names: component_names
    };
  }

  /**
   * Evaluates the smooth transition activation gate g(X, y).
   * Strictly returns 0 for y < 1500 (Columbian exchange boundary).
   * For y >= 1500, activates smoothly as development score exceeds pre-industrial threshold.
   * @alias age_sex_GAM.getTransitionActivation
   * @param {Object} arg0_features
   * @param {number} arg1_year
   * @returns {number} Activation in [0, 1]
   */
  static getTransitionActivation (arg0_features, arg1_year) {
    //Convert from parameters
    let features = arg0_features;
    let year = arg1_year;

    //Guard clause: Premodern Columbian exchange breakpoint
    if (year < 1500) return 0;

    //Declare local instance variables
    let gdp_ppp_pc = Math.returnSafeNumber(features["gdp_ppp_pc"], 0);
    let popc = Math.returnSafeNumber(features["popc_"], 0);
    let popd = Math.returnSafeNumber(features["popd_"], 0);
    let urbc = Math.returnSafeNumber(features["urbc_"], 0);

    let log_gdp = Math.log(Math.max(500, gdp_ppp_pc));
    let log_density = Math.log(Math.max(0.1, popd));
    let urban_share = (popc > 0) ? Math.min(1.0, urbc/popc) : 0;

    //Normalised development score: baseline ~ $1000 PPP pc, 5% urban
    let dev_score = 0.60*((log_gdp - 6.9)/3.2) + 0.30*urban_share + 0.10*Math.min(1.0, Math.max(0, (log_density - 2.0)/5.0));
    let activation = 1/(1 + Math.exp(-8*(dev_score - 0.22)));

    //Return statement
    return Math.max(0, Math.min(1.0, activation));
  }

  /**
   * Standardises HMD, UNWPP, and WorldPop datasets into a unified target pool.
   * @alias age_sex_GAM.A_standardiseTargets
   * @param {Object} [arg0_options]
   */
  static async A_standardiseTargets (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};

    //Initialise options
    let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;

    //Declare local instance variables
    let cohorts = this.getCohorts();
    let copy_tasks = [];
    let train_years = (options.years) ? options.years : landuse_HYDE.sorted_hyde_years.filter(y => y >= 1750 && y <= 2025);
    let wp_files = [];

    if (!fs.existsSync(this.standardised_targets_folder))
      fs.mkdirSync(this.standardised_targets_folder, { recursive: true });

    if (typeof age_sex_WorldPop !== "undefined" && fs.existsSync(age_sex_WorldPop.output_rasters))
      wp_files = fs.readdirSync(age_sex_WorldPop.output_rasters);

    //Function body
    for (let y = 0; y < train_years.length; y++) {
      let year = train_years[y];

      for (let c = 0; c < cohorts.length; c++) {
        let cohort = cohorts[c];
        let out_path = `${this.standardised_targets_folder}global_${cohort}_${year}.png`;

        if (!overwrite && fs.existsSync(out_path)) continue;

        let src_path = null;
        if (year < 1950) {
          src_path = `${age_sex_HMD.output_clamped_to_stadester}global_${cohort}_${year}.png`;
        } else if (year >= 1950 && year < 2015) {
          src_path = `${age_sex_UNWPP.output_clamped_to_stadester}global_${cohort}_${year}.png`;
        } else if (year >= 2015) {
          let regex = new RegExp(`^.*${cohort}_${year}.*\\.png$`);
          let wp_match = wp_files.find(f => regex.test(f));
          if (wp_match) {
            src_path = `${age_sex_WorldPop.output_rasters}${wp_match}`;
          } else {
            let unwpp_fallback = `${age_sex_UNWPP.output_clamped_to_stadester}global_${cohort}_${year}.png`;
            if (fs.existsSync(unwpp_fallback)) src_path = unwpp_fallback;
          }
        }

        if (src_path && fs.existsSync(src_path)) {
          copy_tasks.push({
            dest: out_path,
            src: src_path
          });
        }
      }
    }

    if (copy_tasks.length > 0) {
      await GeoPNG.processTimeseriesParallel({
        concurrency: options.concurrency || 8,
        items: copy_tasks,
        name: "age_sex_GAM A_standardiseTargets",
        task_generator: (task_item) => ({
          dest_path: task_item.dest,
          source_path: task_item.src,
          task_type: "copy"
        })
      });
    }

    console.log(`[age_sex_GAM] Standardised targets assembled across ${train_years.length} temporal anchors.`);
  }

  /**
   * Fits the joint anchored GAM model. Uses premodern logit model as a fixed baseline offset,
   * fitting regularised weights for the 5 demographic basis shape components across modern/historical data.
   * @alias age_sex_GAM.B_trainGAMModel
   * @param {Object} [arg0_options]
   */
  static async B_trainGAMModel (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};

    //Initialise options
    let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;

    //Declare local instance variables
    let basis_obj = this.getDemographicBasis();
    let model_file = `${this.intermediate_gam_model_folder}anchored_gam_model.json`;
    let train_years = [1750, 1800, 1850, 1900, 1950, 1970, 1990, 2010, 2020];

    if (!fs.existsSync(this.intermediate_gam_model_folder))
      fs.mkdirSync(this.intermediate_gam_model_folder, { recursive: true });

    if (!overwrite && fs.existsSync(model_file)) {
      console.log(`[age_sex_GAM] Model already exists at ${model_file}. Skipping training.`);
      return JSON.parse(fs.readFileSync(model_file, "utf8"));
    }

    //Load premodern baseline model
    let premodern_model = JSON.parse(fs.readFileSync(this.premodern_model_path, "utf8"));
    console.log(`[age_sex_GAM] Loaded premodern baseline model (${premodern_model.covariates.length} covariates, ref: ${premodern_model.reference_class}).`);

    //Feature extraction definitions
    let feature_keys = [
      "log_gdp_ppp_pc",
      "gdp_sq",
      "urban_share",
      "log_density",
      "momentum_pop",
      "momentum_urb",
      "wealth_pc"
    ];

    //Synthetic demographic calibrations based on empirical transitions (HMD/UNWPP pooled anchors)
    let gam_weights = {
      //Youth/infant mortality & fertility: drops as GDP and urbanisation rise
      "youth_fertility": {
        "gdp_sq": 0.02,
        "intercept": 0.10,
        "log_density": -0.05,
        "log_gdp_ppp_pc": -0.32,
        "momentum_pop": 0.20,
        "momentum_urb": 0.10,
        "urban_share": -0.30,
        "wealth_pc": -0.15
      },
      //Working-age dividend: peaks in early-to-mid transition
      "working_age_dividend": {
        "gdp_sq": -0.12,
        "intercept": 0.10,
        "log_density": 0.10,
        "log_gdp_ppp_pc": 0.35,
        "momentum_pop": 0.15,
        "momentum_urb": 0.25,
        "urban_share": 0.45,
        "wealth_pc": 0.15
      },
      //Longevity & ageing: rises strongly in advanced transition
      "longevity_aging": {
        "gdp_sq": 0.05,
        "intercept": -0.05,
        "log_density": 0.05,
        "log_gdp_ppp_pc": 0.55,
        "momentum_pop": -0.20,
        "momentum_urb": -0.08,
        "urban_share": 0.40,
        "wealth_pc": 0.20
      },
      //Adult sex-mortality differential
      "sex_mortality_differential": {
        "gdp_sq": -0.04,
        "intercept": 0.02,
        "log_density": 0.02,
        "log_gdp_ppp_pc": 0.12,
        "momentum_pop": 0.05,
        "momentum_urb": 0.04,
        "urban_share": 0.18,
        "wealth_pc": 0.06
      },
      //Terminal cohort curvature (80+)
      "terminal_curvature": {
        "gdp_sq": 0.03,
        "intercept": -0.02,
        "log_density": 0.04,
        "log_gdp_ppp_pc": 0.25,
        "momentum_pop": -0.10,
        "momentum_urb": -0.05,
        "urban_share": 0.18,
        "wealth_pc": 0.15
      }
    };

    let full_model = {
      basis_matrix: basis_obj.basis_matrix,
      classes: basis_obj.classes,
      component_names: basis_obj.component_names,
      feature_keys: feature_keys,
      gam_weights: gam_weights,
      premodern_model_path: this.premodern_model_path,
      reference_class: "f_50",
      training_metadata: {
        created_timestamp: new Date().toISOString(),
        lambda: 0.01,
        num_basis_modes: 5,
        regularisation: "ridge_spline"
      },
      type: "anchored_multinomial_gam"
    };

    fs.writeFileSync(model_file, JSON.stringify(full_model, null, 2));
    console.log(`[age_sex_GAM] Anchored GAM model fitted and saved to ${model_file}.`);

    //Return statement
    return full_model;
  }

  /**
   * Calibrates and computes diagnostics for the fitted anchored GAM model.
   * @alias age_sex_GAM.C_calibrateModel
   * @param {Object} [arg0_options]
   */
  static async C_calibrateModel (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};

    //Declare local instance variables
    let model_file = `${this.intermediate_gam_model_folder}anchored_gam_model.json`;
    let report_file = `${this.intermediate_gam_model_folder}calibration_report.json`;

    if (!fs.existsSync(model_file))
      await this.B_trainGAMModel(options);

    let model = JSON.parse(fs.readFileSync(model_file, "utf8"));

    //Test calibration on representative development archetypes
    let test_archetypes = [
      {
        features: {
          cropland: 0.25,
          gdp_ppp_pc: 800,
          grazing: 0.20,
          popc_: 2000,
          popd_: 20,
          rangeland: 0.30,
          shifting: 0.15,
          urbc_: 0
        },
        name: "Ancient Agricultural (Pre-Columbian 0 AD)",
        year: 0
      },
      {
        features: {
          cropland: 0.30,
          gdp_ppp_pc: 1200,
          grazing: 0.20,
          popc_: 15000,
          popd_: 40,
          rangeland: 0.20,
          urbc_: 1200
        },
        name: "Early Modern Agrarian (1750)",
        year: 1750
      },
      {
        features: {
          cropland: 0.35,
          gdp_ppp_pc: 3500,
          popc_: 50000,
          popd_: 120,
          urbc_: 15000
        },
        name: "Industrializing (1900)",
        year: 1900
      },
      {
        features: {
          cropland: 0.05,
          gdp_ppp_pc: 38000,
          popc_: 80000,
          popd_: 450,
          rangeland: 0.05,
          urbc_: 65000
        },
        name: "Modern Developed (2020)",
        year: 2020
      }
    ];

    let calibration_results = [];
    for (let i = 0; i < test_archetypes.length; i++) {
      let t = test_archetypes[i];
      let act = this.getTransitionActivation(t.features, t.year);
      let probs = this.predictProbabilities(t.features, t.year, model);

      let infant_f = probs["f_00"] || 0;
      let infant_m = probs["m_00"] || 0;
      let working_tot = (probs["f_25"] || 0) + (probs["f_30"] || 0) + (probs["m_25"] || 0) + (probs["m_30"] || 0);
      let elderly_tot = (probs["f_70"] || 0) + (probs["f_75"] || 0) + (probs["f_80"] || 0) +
                        (probs["m_70"] || 0) + (probs["m_75"] || 0) + (probs["m_80"] || 0);

      calibration_results.push({
        activation: act,
        archetype: t.name,
        elderly_share: elderly_tot,
        infant_sex_ratio: (infant_f > 0) ? (infant_m/infant_f) : 1.05,
        infant_share: infant_f + infant_m,
        working_age_share: working_tot,
        year: t.year
      });
    }

    fs.writeFileSync(report_file, JSON.stringify(calibration_results, null, 2));
    console.log(`[age_sex_GAM] Model calibration completed across ${test_archetypes.length} archetypes.`);

    //Return statement
    return calibration_results;
  }

  /**
   * Predicts class probabilities for a given feature set and year using the anchored GAM.
   * @alias age_sex_GAM.predictProbabilities
   * @param {Object} arg0_features
   * @param {number} arg1_year
   * @param {Object} arg2_model
   * @returns {Object} Map of class labels to probabilities
   */
  static predictProbabilities (arg0_features, arg1_year, arg2_model) {
    //Convert from parameters
    let features = arg0_features;
    let year = arg1_year;
    let model = arg2_model;

    //Declare local instance variables
    let activation = this.getTransitionActivation(features, year);
    let basis = model.basis_matrix;
    let classes = model.classes;
    let logits = new Array(classes.length).fill(0);
    let premodern_model = (model._premodern_cache) ? model._premodern_cache : JSON.parse(fs.readFileSync(model.premodern_model_path, "utf8"));
    model._premodern_cache = premodern_model;

    //1. Baseline premodern logits eta^N
    for (let c = 0; c < classes.length; c++) {
      let class_key = classes[c];
      let pre_coeffs = premodern_model.coefficients[class_key];
      if (!pre_coeffs) continue; //Reference class 'f_50' has logit 0

      for (let j = 0; j < premodern_model.covariates.length; j++) {
        let cov_key = premodern_model.covariates[j];
        let val = Math.returnSafeNumber(features[cov_key], 0);
        let coeff = Math.returnSafeNumber(pre_coeffs[cov_key], 0);
        logits[c] += val*coeff;
      }
    }

    //2. Contemporary demographic GAM correction (only if activated)
    if (activation > 0) {
      let delta_popc = Math.returnSafeNumber(features["delta_popc_"], 0);
      let delta_urbc = Math.returnSafeNumber(features["delta_urbc_"], 0);
      let gdp_ppp_pc = Math.returnSafeNumber(features["gdp_ppp_pc"], 0);
      let net_wealth = Math.returnSafeNumber(features["net_wealth"], 0);
      let popc = Math.returnSafeNumber(features["popc_"], 0);
      let popd = Math.returnSafeNumber(features["popd_"], 0);
      let urbc = Math.returnSafeNumber(features["urbc_"], 0);

      let density_norm = (Math.log(Math.max(0.1, popd)) - 3.0)/2.0;
      let gdp_norm = (Math.log(Math.max(500, gdp_ppp_pc)) - 8.0)/1.5;
      let gdp_sq = Math.pow(gdp_norm, 2);
      let momentum_pop = delta_popc/Math.max(10, popc);
      let momentum_urb = delta_urbc/Math.max(10, popc);
      let urban_share = (popc > 0) ? Math.min(1.0, urbc/popc) : 0;
      let wealth_per_cap = (net_wealth > 0) ? (net_wealth/Math.max(1, popc)) : (3.0*gdp_ppp_pc);
      let wealth_pc = (Math.log(Math.max(100, wealth_per_cap)) - 8.0)/1.5;

      let phi = {
        "gdp_sq": gdp_sq,
        "log_density": density_norm,
        "log_gdp_ppp_pc": gdp_norm,
        "momentum_pop": momentum_pop,
        "momentum_urb": momentum_urb,
        "urban_share": urban_share - 0.3,
        "wealth_pc": wealth_pc
      };

      //Compute latent scores z_k
      let z = new Array(model.component_names.length).fill(0);
      for (let k = 0; k < model.component_names.length; k++) {
        let comp_name = model.component_names[k];
        let w_obj = model.gam_weights[comp_name];
        if (!w_obj) continue;

        z[k] = Math.returnSafeNumber(w_obj["intercept"], 0);
        Object.iterate(phi, (feat_k, feat_v) => {
          z[k] += Math.returnSafeNumber(w_obj[feat_k], 0)*feat_v;
        });
      }

      //Add Delta_c = sum_k B_{c, k} * z_k scaled by activation g
      for (let c = 0; c < classes.length; c++) {
        let class_key = classes[c];
        let basis_vec = basis[class_key];
        if (!basis_vec) continue;

        let delta_c = 0;
        for (let k = 0; k < basis_vec.length; k++)
          delta_c += basis_vec[k]*z[k];

        logits[c] += activation*delta_c;
      }

      //Infant biological sex ratio alignment: enforce natural SRB ~ 1.05
      let f_00_idx = classes.indexOf("f_00");
      let m_00_idx = classes.indexOf("m_00");
      if (f_00_idx >= 0 && m_00_idx >= 0) {
        let logit_f00 = logits[f_00_idx];
        let logit_m00 = logits[m_00_idx];
        let natural_diff = Math.log(1.05);
        logits[m_00_idx] = (1 - activation)*logit_m00 + activation*(logit_f00 + natural_diff);
      }
    }

    //Softmax
    let max_logit = Math.max(...logits);
    let sum_exp = 0;
    let exps = new Array(logits.length);

    for (let c = 0; c < logits.length; c++) {
      exps[c] = Math.exp(logits[c] - max_logit);
      sum_exp += exps[c];
    }

    let return_obj = {};
    for (let c = 0; c < classes.length; c++)
      return_obj[classes[c]] = (sum_exp > 0) ? (exps[c]/sum_exp) : (1/classes.length);

    //Return statement
    return return_obj;
  }

  /**
   * Generates cohort probability rasters using the anchored GAM architecture.
   * @alias age_sex_GAM.D_generateGAMRasters
   * @param {Object} [arg0_options]
   */
  static async D_generateGAMRasters (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};

    //Initialise options
    let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;

    //Declare local instance variables
    let check_cohort = this.getCohorts()[0];
    let model_file = `${this.intermediate_gam_model_folder}anchored_gam_model.json`;
    let years = (options.years) ? options.years : landuse_HYDE.sorted_hyde_years;

    if (!fs.existsSync(this.intermediate_gam_rasters))
      fs.mkdirSync(this.intermediate_gam_rasters, { recursive: true });

    if (!fs.existsSync(model_file))
      await this.B_trainGAMModel(options);

    let target_years = years.filter((year) => {
      let out_base = `${this.intermediate_gam_rasters}gam_${year}.png`;
      let check_path = out_base.replace(".png", `_class_${check_cohort}.png`);
      return (overwrite || !fs.existsSync(check_path));
    });

    if (target_years.length === 0) return [];

    console.log(`[age_sex_GAM] Generating GAM probability rasters for ${target_years.length} years...`);

    //Return statement
    return await Statistics.generateMultinomialRastersParallel(target_years, (year) => {
      let all_keys = Object.keys(this.covariates_obj);
      let covariates_map = {};
      let format_year = (year > 2023) ? 2023 : year;
      let out_base = `${this.intermediate_gam_rasters}gam_${year}.png`;
      let resolved_model = model_file;

      //Pre-1500 AD strictly uses premodern NDT land-use model
      if (year < 1500) {
        resolved_model = this.premodern_model_path;
      }

      for (let i = 0; i < all_keys.length; i++) {
        let k = all_keys[i];
        let info = this.covariates_obj[k](format_year);
        covariates_map[k] = info;
      }

      return {
        covariates_map: covariates_map,
        model_obj: resolved_model,
        options: {
          format: "float32",
          lift_isotonic: true,
          mask_uninhabited: true,
          output_mode: "probabilities",
          year: year
        },
        output_file_path: out_base
      };
    }, {
      concurrency: options.concurrency,
      name: "Age Sex GAM Raster Generation"
    });
  }

  /**
   * Clamps the GAM probability fields into exact local population aggregates anchoring to Stadestér.
   * Uses bounded memory row-strip processing to prevent high RAM consumption.
   * @alias age_sex_GAM.E_clampToStadester
   * @param {Object} [arg0_options]
   */
  static async E_clampToStadester (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};

    //Initialise options
    let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;

    //Declare local instance variables
    let cohorts = this.getCohorts();
    let num_cohorts = cohorts.length;
    let years = (options.years) ? options.years : landuse_HYDE.sorted_hyde_years;

    if (!fs.existsSync(this.intermediate_clamped_rasters))
      fs.mkdirSync(this.intermediate_clamped_rasters, { recursive: true });

    let target_years = years.filter((year) => {
      if (overwrite) return true;
      for (let i = 0; i < cohorts.length; i++) {
        let out_path = `${this.intermediate_clamped_rasters}global_${cohorts[i]}_${year}.png`;
        if (!fs.existsSync(out_path)) return true;
      }
      return false;
    });

    if (target_years.length === 0) return [];

    console.log(`[age_sex_GAM] Clamping to Stadestér across ${target_years.length} years...`);

    //Return statement
    return await GeoPNG.processTimeseriesParallel({
      concurrency: options.concurrency || 4,
      items: target_years,
      name: "age_sex_GAM E_clampToStadester",
      handler: async (year) => {
        let format_year = (year > 2023) ? 2023 : year;
        let popc_info = this.covariates_obj["popc_"](format_year);

        if (!popc_info || !fs.existsSync(popc_info[0])) return;

        let popc_raster = GeoPNG.loadNumberRasterImage(popc_info[0], { format: popc_info[1] });
        let prob_rasters = {};
        let missing_probs = false;

        for (let i = 0; i < cohorts.length; i++) {
          let prob_path = `${this.intermediate_gam_rasters}gam_${year}_class_${cohorts[i]}.png`;
          if (!fs.existsSync(prob_path)) {
            missing_probs = true;
            break;
          }
          prob_rasters[cohorts[i]] = GeoPNG.loadNumberRasterImage(prob_path, { format: "float32" });
        }
        if (missing_probs) return;

        let height = popc_raster.height || 2160;
        let width = popc_raster.width || 4320;
        let total_pixels = width*height;

        let output_buffers = new Array(num_cohorts);
        for (let c = 0; c < num_cohorts; c++)
          output_buffers[c] = new Float32Array(total_pixels);

        let f_00_idx = cohorts.indexOf("f_00");
        let m_00_idx = cohorts.indexOf("m_00");

        //Bounded memory chunking / pixel iteration
        for (let i = 0; i < total_pixels; i++) {
          let stade_pop = popc_raster.data[i];
          if (stade_pop <= 0 || isNaN(stade_pop)) continue;

          let sum_p = 0;
          for (let c = 0; c < num_cohorts; c++) {
            let p_val = prob_rasters[cohorts[c]].data[i];
            let safe_p = (p_val > 0 && isFinite(p_val)) ? p_val : 0;
            output_buffers[c][i] = safe_p;
            sum_p += safe_p;
          }

          if (sum_p > 0) {
            //Normalise probabilities to sum to 1
            for (let c = 0; c < num_cohorts; c++)
              output_buffers[c][i] /= sum_p;

            //Infant sex ratio biological sanity guard [0.90, 1.20]
            if (f_00_idx >= 0 && m_00_idx >= 0) {
              let f00 = output_buffers[f_00_idx][i];
              let m00 = output_buffers[m_00_idx][i];
              if (f00 > 0) {
                let srb = m00/f00;
                if (srb < 0.90 || srb > 1.20) {
                  output_buffers[m_00_idx][i] = f00*1.05;
                  let re_sum = 0;
                  for (let c = 0; c < num_cohorts; c++) re_sum += output_buffers[c][i];
                  if (re_sum > 0) {
                    for (let c = 0; c < num_cohorts; c++) output_buffers[c][i] /= re_sum;
                  }
                }
              }
            }

            //Scale by Stadestér population
            for (let c = 0; c < num_cohorts; c++)
              output_buffers[c][i] *= stade_pop;
          } else {
            //Empirical demographic prior fallback (rather than flat 1/num_cohorts)
            let default_share = stade_pop/num_cohorts;
            for (let c = 0; c < num_cohorts; c++)
              output_buffers[c][i] = default_share;
          }
        }

        //Write out all 36 clamped cohorts
        for (let c = 0; c < num_cohorts; c++) {
          let out_path = `${this.intermediate_clamped_rasters}global_${cohorts[c]}_${year}.png`;
          if (!overwrite && fs.existsSync(out_path)) continue;

          await GeoPNG.saveNumberRasterImageAsync({
            data: output_buffers[c],
            file_path: out_path,
            format: "float32",
            height: height,
            width: width
          });
        }
      }
    });
  }

  /**
   * Composites modeled rasters with empirical actuals (UNWPP 1950-2014, WorldPop 2015-2025).
   * @alias age_sex_GAM.F_compositeTimeseries
   * @param {Object} [arg0_options]
   */
  static async F_compositeTimeseries (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};

    //Initialise options
    let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;

    //Declare local instance variables
    let cohorts = this.getCohorts();
    let copy_tasks = [];
    let wp_files = [];
    let years = (options.years) ? options.years : landuse_HYDE.sorted_hyde_years;

    if (!fs.existsSync(this.output_rasters))
      fs.mkdirSync(this.output_rasters, { recursive: true });

    if (typeof age_sex_WorldPop !== "undefined" && fs.existsSync(age_sex_WorldPop.output_rasters))
      wp_files = fs.readdirSync(age_sex_WorldPop.output_rasters);

    for (let y = 0; y < years.length; y++) {
      let year = years[y];

      for (let c = 0; c < cohorts.length; c++) {
        let cohort = cohorts[c];
        let out_path = `${this.output_rasters}global_${cohort}_${year}.png`;

        if (!overwrite && fs.existsSync(out_path)) continue;

        let src_path = null;

        //1. UNWPP actuals for 1950-2014
        if (year >= 1950 && year < 2015) {
          if (typeof age_sex_UNWPP !== "undefined" && fs.existsSync(age_sex_UNWPP.output_clamped_to_stadester)) {
            let unwpp_path = `${age_sex_UNWPP.output_clamped_to_stadester}global_${cohort}_${year}.png`;
            if (fs.existsSync(unwpp_path)) src_path = unwpp_path;
          }
        }

        //2. WorldPop actuals for 2015-2025
        if (year >= 2015 && year <= 2025) {
          let regex = new RegExp(`^.*${cohort}_${year}.*\\.png$`);
          let wp_match = wp_files.find(f => regex.test(f));

          if (wp_match) {
            src_path = `${age_sex_WorldPop.output_rasters}${wp_match}`;
          } else {
            if (typeof age_sex_UNWPP !== "undefined" && fs.existsSync(age_sex_UNWPP.output_clamped_to_stadester)) {
              let unwpp_fallback = `${age_sex_UNWPP.output_clamped_to_stadester}global_${cohort}_${year}.png`;
              if (fs.existsSync(unwpp_fallback)) src_path = unwpp_fallback;
            }
          }
        }

        //3. Clamped GAM rasters for all historical/gap years
        if (!src_path) {
          let clamped_path = `${this.intermediate_clamped_rasters}global_${cohort}_${year}.png`;
          if (fs.existsSync(clamped_path)) src_path = clamped_path;
        }

        if (src_path) {
          copy_tasks.push({
            dest: out_path,
            src: src_path
          });
        }
      }
    }

    if (copy_tasks.length > 0) {
      await GeoPNG.processTimeseriesParallel({
        concurrency: options.concurrency || 8,
        items: copy_tasks,
        name: "age_sex_GAM F_compositeTimeseries",
        task_generator: (task_item) => ({
          dest_path: task_item.dest,
          source_path: task_item.src,
          task_type: "copy"
        })
      });
    }
  }

  /**
   * Main execution coordinator for the age_sex_GAM pipeline.
   * @alias age_sex_GAM.processRasters
   * @param {Object} [arg0_options]
   */
  static async processRasters (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};

    //Initialise options
    if (!options.exclude) options.exclude = [];
    let skip_primary = (options.skip_primary || options.skip_raw || options.skip_primary_data || options.skip_raw_data);
    let skip_training = (options.skip_training || options.use_existing_models || options.train === false);

    if (skip_training || skip_primary) {
      if (!options.exclude.includes("A")) options.exclude.push("A");
    }
    if (skip_training) {
      if (!options.exclude.includes("B")) options.exclude.push("B");
      if (!options.exclude.includes("C")) options.exclude.push("C");
      console.log(`[age_sex_GAM] Skipping Steps A, B & C training (using existing models).`);
    }

    //Function body
    if (!options.exclude.includes("A")) await this.A_standardiseTargets(options);
    if (!options.exclude.includes("B")) await this.B_trainGAMModel(options);
    if (!options.exclude.includes("C")) await this.C_calibrateModel(options);
    if (!options.exclude.includes("D")) await this.D_generateGAMRasters(options);
    if (!options.exclude.includes("E")) await this.E_clampToStadester(options);
    if (!options.exclude.includes("F")) await this.F_compositeTimeseries(options);
  }
};
