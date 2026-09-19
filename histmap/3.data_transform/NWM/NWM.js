//Initialise functions
{
  if (!global.NWM) global.NWM = {};
  
  /**
   * Master orchestrator for the National / World Model (NWM) historical demographic,
   * urban settlement, and macroeconomic raster pipeline.
   * 
   * Coordinates end-to-end timeseries execution across Substrata, Stadestér, Eoscala GDP,
   * Covariates, Gini, Wealth/Income, Age/Sex population pyramids, Births/Deaths, and Professions.
   * 
   * @class NWM
   */
  global.NWM = class {
    /**
     * Loads all required pipeline dependency classes if not already present in the global scope.
     * @alias NWM.loadDependencies
     * 
     * @param {Object} [arg0_options]
     */
    static loadDependencies (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Declare local instance variables
      let dep_keys;
      let dep_map = {
        landuse_HYDE: (global.h2) ? path.join(h2, "landuse_HYDE", "landuse_HYDE.js") : "",
        population_Substrata_outlier_removal: (global.h3) ? path.join(h3, "population_Substrata.outlier_removal", "population_Substrata_outlier_removal.js") : "",
        population_Stadester: (global.h2) ? path.join(h2, "population_Stadester", "population_Stadester.js") : "",
        GDP_PPP_SEDAC: (global.h2) ? path.join(h2, "GDP_PPP_SEDAC", "GDP_PPP_SEDAC.js") : "",
        GDP_nominal_SEDAC: (global.h2) ? path.join(h2, "GDP_nominal_SEDAC", "GDP_nominal_SEDAC.js") : "",
        GDP_PPP_OLS: (global.h2) ? path.join(h2, "GDP_PPP_OLS", "GDP_PPP_OLS.js") : "",
        GDP_PPP: (global.h3) ? path.join(h3, "GDP_PPP", "GDP_PPP.js") : "",
        GDP_nominal_OLS: (global.h2) ? path.join(h2, "GDP_nominal_OLS", "GDP_nominal_OLS.js") : "",
        GDP_nominal: (global.h2) ? path.join(h2, "GDP_nominal", "GDP_nominal.js") : "",
        GDP_PPP_pc: (global.h3) ? path.join(h3, "GDP_PPP_pc", "GDP_PPP_pc.js") : "",
        GDP_pc: (global.h3) ? path.join(h3, "GDP_pc", "GDP_pc.js") : "",
        population_Stadester_transform: (global.h3) ? path.join(h3, "population_Stadester.transform", "population_Stadester_transform.js") : "",
        GDP_Eoscala_transform: (global.h3) ? path.join(h3, "GDP_Eoscala.transform", "GDP_Eoscala_transform.js") : "",
        gini_OLS: (global.h2) ? path.join(h2, "gini_OLS", "gini_OLS.js") : "",
        gini_Eoscala: (global.h2) ? path.join(h2, "gini_Eoscala", "gini_Eoscala.js") : "",
        wealth_income_WID: (global.h2) ? path.join(h2, "wealth_income_WID", "wealth_income_WID.js") : "",
        wealth_income_OLS: (global.h2) ? path.join(h2, "wealth_income_OLS", "wealth_income_OLS.js") : "",
        wealth_income: (global.h3) ? path.join(h3, "wealth_income", "wealth_income.js") : "",
        age_sex_WorldPop: (global.h2) ? path.join(h2, "age_sex_WorldPop", "age_sex_WorldPop.js") : "",
        age_sex_UNWPP: (global.h2) ? path.join(h2, "age_sex_UNWPP", "age_sex_UNWPP.js") : "",
        age_sex_HMD: (global.h2) ? path.join(h2, "age_sex_HMD", "age_sex_HMD.js") : "",
        age_sex: (global.h3) ? path.join(h3, "age_sex", "age_sex.js") : "",
        births_deaths_Kummu: (global.h2) ? path.join(h2, "births_deaths_Kummu", "births_deaths_Kummu.js") : "",
        births_deaths_UNWPP: (global.h2) ? path.join(h2, "births_deaths_UNWPP", "births_deaths_UNWPP.js") : "",
        births_deaths_HMD: (global.h2) ? path.join(h2, "births_deaths_HMD", "births_deaths_HMD.js") : "",
        births_deaths_OLS: (global.h2) ? path.join(h2, "births_deaths_OLS", "births_deaths_OLS.js") : "",
        LFPR_ILO: (global.h2) ? path.join(h2, "LFPR_ILO", "LFPR_ILO.js") : "",
        LFPR_Olivetti: (global.h2) ? path.join(h2, "LFPR_Olivetti", "LFPR_Olivetti.js") : "",
        LFPR_OLS: (global.h2) ? path.join(h2, "LFPR_OLS", "LFPR_OLS.js") : "",
        professions_ILO: (global.h2) ? path.join(h2, "professions_ILO", "professions_ILO.js") : "",
        professions_Olivetti: (global.h2) ? path.join(h2, "professions_Olivetti", "professions_Olivetti.js") : "",
        professions: (global.h3) ? path.join(h3, "professions", "professions.js") : ""
      };
      
      //Function body
      dep_keys = Object.keys(dep_map);
      for (let i = 0; i < dep_keys.length; i++) {
        let key = dep_keys[i];
        if (!global[key] && typeof require !== "undefined" && dep_map[key]) {
          try {
            if (fs.existsSync(dep_map[key])) require(path.resolve(dep_map[key]));
          } catch (e) {
            console.warn(`[NWM] Failed to auto-load dependency ${key}:`, e);
          }
        }
      }
    }
    
    /**
     * Step A: Processes HYDE land use rasters and Velkscala Substrata population outlier removal.
     * @alias NWM.A_processSubstrata
     * 
     * @param {Object} [arg0_options]
     *  @param {Object} [arg0_options.hyde] - Options passed to landuse_HYDE.processRasters
     *  @param {Object} [arg0_options.substrata] - Options passed to population_Substrata_outlier_removal.processRasters
     */
    static async A_processSubstrata (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Declare local instance variables
      let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
      
      let hyde_options = { exclude: ["A"], overwrite: overwrite, ...(options.hyde || {}) };
      let substrata_options = { overwrite: overwrite, ...(options.substrata || {}) };
      
      //Function body
      console.log(`[NWM] === Step A: Processing Substrata & HYDE Land Use ===`);
      if (global.landuse_HYDE) await landuse_HYDE.processRasters(hyde_options);
      if (global.population_Substrata_outlier_removal)
        await population_Substrata_outlier_removal.processRasters(substrata_options);
    }
    
    /**
     * Step B: Processes the Stadestér Historical GIS City & Raster Demographics pipeline.
     * Integrates concentric radial walkability buffering, float32 processing, annular pixel correction, and GHSL city repair.
     * @alias NWM.B_processStadester
     * 
     * @param {Object} [arg0_options]
     *  @param {Object} [arg0_options.stadester] - Options passed to population_Stadester.processRasters
     */
    static async B_processStadester (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Declare local instance variables
      let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
      let stadester_options = { overwrite: overwrite, ...(options.stadester || {}) };
      
      //Function body
      console.log(`[NWM] === Step B: Processing Stadestér Demographics & Rasters ===`);
      if (global.population_Stadester)
        await population_Stadester.processRasters(stadester_options);
    }
    
    /**
     * Step C: Processes Eoscala Historical GDP (PPP & Nominal) from SEDAC baselines, OLS spatial downscaling, and dasymetric reconciliation.
     * @alias NWM.C_processEoscalaGDP
     * 
     * @param {Object} [arg0_options]
     *  @param {Object} [arg0_options.gdp_nominal]
     *  @param {Object} [arg0_options.gdp_nominal_ols]
     *  @param {Object} [arg0_options.gdp_nominal_sedac]
     *  @param {Object} [arg0_options.gdp_ppp]
     *  @param {Object} [arg0_options.gdp_ppp_ols]
     *  @param {Object} [arg0_options.gdp_ppp_sedac]
     */
    static async C_processEoscalaGDP (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Declare local instance variables
      let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
      let skip_training = (options.skip_training || options.use_existing_models || options.train === false);
      
      let gdp_nom_ols_options = { overwrite: overwrite, ...(options.gdp_nominal_ols || {}) };
      let gdp_nom_options = { overwrite: overwrite, ...(options.gdp_nominal || {}) };
      let gdp_nom_sedac_options = { exclude: ["A"], overwrite: overwrite, ...(options.gdp_nominal_sedac || {}) };
      let gdp_ppp_ols_options = { overwrite: overwrite, ...(options.gdp_ppp_ols || {}) };
      let gdp_ppp_options = { overwrite: overwrite, ...(options.gdp_ppp || {}) };
      let gdp_ppp_sedac_options = { exclude: ["A"], overwrite: overwrite, ...(options.gdp_ppp_sedac || {}) };

      if (skip_training) {
        if (!gdp_ppp_sedac_options.exclude) gdp_ppp_sedac_options.exclude = [];
        if (!gdp_ppp_sedac_options.exclude.includes("B")) gdp_ppp_sedac_options.exclude.push("B");
        if (!gdp_ppp_sedac_options.exclude.includes("C")) gdp_ppp_sedac_options.exclude.push("C");
        gdp_ppp_sedac_options.skip_training = true;

        if (!gdp_nom_sedac_options.exclude) gdp_nom_sedac_options.exclude = [];
        if (!gdp_nom_sedac_options.exclude.includes("B")) gdp_nom_sedac_options.exclude.push("B");
        if (!gdp_nom_sedac_options.exclude.includes("C")) gdp_nom_sedac_options.exclude.push("C");
        gdp_nom_sedac_options.skip_training = true;

        console.log(`[NWM] Step C: Skipping GDP_PPP_SEDAC and GDP_nominal_SEDAC OLS training (using existing models).`);
      }
      
      //Function body
      console.log(`[NWM] === Step C: Processing Eoscala GDP (PPP & Nominal) ===`);
      if (global.GDP_PPP_SEDAC) await GDP_PPP_SEDAC.processRasters(gdp_ppp_sedac_options);
      if (global.GDP_nominal_SEDAC) await GDP_nominal_SEDAC.processRasters(gdp_nom_sedac_options);
      
      if (global.GDP_PPP_OLS) await GDP_PPP_OLS.processRasters(gdp_ppp_ols_options);
      if (global.GDP_PPP) await GDP_PPP.processRasters(gdp_ppp_options);
      
      if (global.GDP_nominal_OLS) await GDP_nominal_OLS.processRasters(gdp_nom_ols_options);
      if (global.GDP_nominal) await GDP_nominal.processRasters(gdp_nom_options);
    }
    
    /**
     * Step D: Computes per capita GDP (PPP pc & Nominal pc) rasters by dividing downscaled GDP by total population.
     * @alias NWM.D_processGDPPerCapita
     * 
     * @param {Object} [arg0_options]
     *  @param {Object} [arg0_options.gdp_pc]
     *  @param {Object} [arg0_options.gdp_ppp_pc]
     *  @param {boolean} [arg0_options.skip_training=false]
     *  @param {boolean} [arg0_options.use_existing_models=false]
     */
    static async D_processGDPPerCapita (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Declare local instance variables
      let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
      let skip_training = (options.skip_training || options.use_existing_models || options.train === false);
      
      let gdp_pc_options = { overwrite: overwrite, ...(options.gdp_pc || {}) };
      let gdp_ppp_pc_options = { overwrite: overwrite, ...(options.gdp_ppp_pc || {}) };
      
      if (skip_training) {
        if (!gdp_pc_options.exclude) gdp_pc_options.exclude = [];
        if (!gdp_pc_options.exclude.includes("B")) gdp_pc_options.exclude.push("B");
        gdp_pc_options.skip_training = true;
        
        if (!gdp_ppp_pc_options.exclude) gdp_ppp_pc_options.exclude = [];
        if (!gdp_ppp_pc_options.exclude.includes("B")) gdp_ppp_pc_options.exclude.push("B");
        gdp_ppp_pc_options.skip_training = true;
        console.log(`[NWM] Step D: Skipping GDP_pc & GDP_PPP_pc regression training (using existing models).`);
      }
      
      //Function body
      console.log(`[NWM] === Step D: Processing Per Capita GDP ===`);
      if (global.GDP_PPP_pc) await GDP_PPP_pc.processRasters(gdp_ppp_pc_options);
      if (global.GDP_pc) await GDP_pc.processRasters(gdp_pc_options);
    }
    
    /**
     * Step E: Generates spatiotemporal delta rasters across population density, rural/urban totals, and GDP series.
     * @alias NWM.E_processCovariates
     * 
     * @param {Object} [arg0_options]
     *  @param {Object} [arg0_options.gdp_eoscala_transform]
     *  @param {Object} [arg0_options.population_stadester_transform]
     */
    static async E_processCovariates (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Declare local instance variables
      let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
      
      let eoscala_transform_options = { overwrite: overwrite, ...(options.gdp_eoscala_transform || options.eoscala_transform || {}) };
      let stadester_transform_options = { overwrite: overwrite, ...(options.population_stadester_transform || options.stadester_transform || {}) };
      
      //Function body
      console.log(`[NWM] === Step E: Processing Covariate Delta Transforms ===`);
      if (global.population_Stadester_transform)
        await population_Stadester_transform.processRasters(stadester_transform_options);
      if (global.GDP_Eoscala_transform)
        await GDP_Eoscala_transform.processRasters(eoscala_transform_options);
    }
    
    /**
     * Step F: Trains spatial regression models and produces global historical Gini coefficient rasters.
     * @alias NWM.F_processGini
     * 
     * @param {Object} [arg0_options]
     *  @param {Object} [arg0_options.gini_eoscala]
     *  @param {Object} [arg0_options.gini_ols]
     *  @param {boolean} [arg0_options.skip_training=false]
     *  @param {boolean} [arg0_options.use_existing_models=false]
     */
    static async F_processGini (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Declare local instance variables
      let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
      let skip_training = (options.skip_training || options.use_existing_models || options.train === false);
      
      let gini_eoscala_options = { overwrite: overwrite, ...(options.gini_eoscala || {}) };
      let gini_ols_options = { overwrite: overwrite, ...(options.gini_ols || {}) };
      
      //Function body
      console.log(`[NWM] === Step F: Processing GINI Inequality ===`);
      if (!skip_training) {
        if (global.gini_OLS) await gini_OLS.processRasters(gini_ols_options);
      } else {
        console.log(`[NWM] Step F: Skipping Gini OLS training (using existing models).`);
      }
      if (global.gini_Eoscala) await gini_Eoscala.processRasters(gini_eoscala_options);
    }
    
    /**
     * Step G: Ingests World Inequality Database (WID) masks, runs OLS learning, and outputs wealth/income distribution rasters.
     * @alias NWM.G_processWealthIncome
     * 
     * @param {Object} [arg0_options]
     *  @param {Object} [arg0_options.wealth_income]
     *  @param {Object} [arg0_options.wealth_income_ols]
     *  @param {Object} [arg0_options.wealth_income_wid]
     *  @param {boolean} [arg0_options.skip_training=false]
     *  @param {boolean} [arg0_options.use_existing_models=false]
     */
    static async G_processWealthIncome (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Declare local instance variables
      let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
      let skip_training = (options.skip_training || options.use_existing_models || options.train === false);
      
      let wealth_income_ols_options = { overwrite: overwrite, ...(options.wealth_income_ols || {}) };
      let wealth_income_options = { overwrite: overwrite, ...(options.wealth_income || {}) };
      let wealth_income_wid_options = { overwrite: overwrite, ...(options.wealth_income_wid || {}) };
      
      //Function body
      console.log(`[NWM] === Step G: Processing Wealth & Income (WID) ===`);
      if (global.wealth_income_WID) await wealth_income_WID.processRasters(wealth_income_wid_options);
      if (!skip_training) {
        if (global.wealth_income_OLS) await wealth_income_OLS.processRasters(wealth_income_ols_options);
      } else {
        console.log(`[NWM] Step G: Skipping wealth_income_OLS training (using existing models).`);
      }
      if (global.wealth_income) await wealth_income.processRasters(wealth_income_options);
    }
    
    /**
     * Step H: Processes WorldPop, UNWPP, and HMD demographic baselines, running multinomial logit regression for population pyramids.
     * @alias NWM.H_processAgeSex
     * 
     * @param {Object} [arg0_options]
     *  @param {Object} [arg0_options.age_sex]
     *  @param {Object} [arg0_options.age_sex_hmd]
     *  @param {Object} [arg0_options.age_sex_unwpp]
     *  @param {Object} [arg0_options.age_sex_worldpop]
     *  @param {boolean} [arg0_options.skip_training=false]
     *  @param {boolean} [arg0_options.use_existing_models=false]
     */
    static async H_processAgeSex (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Declare local instance variables
      let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
      let skip_training = (options.skip_training || options.use_existing_models || options.train === false);
      
      let age_sex_hmd_options = { overwrite: overwrite, ...(options.age_sex_hmd || {}) };
      let age_sex_options = { overwrite: overwrite, ...(options.age_sex || {}) };
      let age_sex_unwpp_options = { overwrite: overwrite, ...(options.age_sex_unwpp || {}) };
      let age_sex_worldpop_options = { overwrite: overwrite, ...(options.age_sex_worldpop || {}) };
      
      if (skip_training) {
        if (!age_sex_options.exclude) age_sex_options.exclude = [];
        if (!age_sex_options.exclude.includes("B")) age_sex_options.exclude.push("B");
        if (!age_sex_options.exclude.includes("C")) age_sex_options.exclude.push("C");
        age_sex_options.skip_training = true;
        console.log(`[NWM] Step H: Skipping Age-Sex Multinomial Logit training (using existing models).`);
      }
      
      //Function body
      console.log(`[NWM] === Step H: Processing Velkscala Age-Sex Population Pyramids ===`);
      if (global.age_sex_WorldPop) await age_sex_WorldPop.processRasters(age_sex_worldpop_options);
      if (global.age_sex_UNWPP) await age_sex_UNWPP.processRasters(age_sex_unwpp_options);
      if (global.age_sex_HMD) await age_sex_HMD.processRasters(age_sex_hmd_options);
      if (global.age_sex) await age_sex.processRasters(age_sex_options);
    }
    
    /**
     * Step I: Models and reconciles spatiotemporal crude birth and death rate rasters across historical eras.
     * @alias NWM.I_processBirthsDeaths
     * 
     * @param {Object} [arg0_options]
     *  @param {Object} [arg0_options.births_deaths_hmd]
     *  @param {Object} [arg0_options.births_deaths_kummu]
     *  @param {Object} [arg0_options.births_deaths_ols]
     *  @param {Object} [arg0_options.births_deaths_unwpp]
     *  @param {boolean} [arg0_options.skip_training=false]
     *  @param {boolean} [arg0_options.use_existing_models=false]
     */
    static async I_processBirthsDeaths (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Declare local instance variables
      let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
      let skip_training = (options.skip_training || options.use_existing_models || options.train === false);
      
      let births_deaths_hmd_options = { overwrite: overwrite, ...(options.births_deaths_hmd || {}) };
      let births_deaths_kummu_options = { overwrite: overwrite, ...(options.births_deaths_kummu || {}) };
      let births_deaths_ols_options = { overwrite: overwrite, skip_training: skip_training, ...(options.births_deaths_ols || {}) };
      let births_deaths_unwpp_options = { overwrite: overwrite, ...(options.births_deaths_unwpp || {}) };
      
      //Function body
      console.log(`[NWM] === Step I: Processing Crude Births & Deaths ===`);
      if (global.births_deaths_Kummu) await births_deaths_Kummu.processRasters(births_deaths_kummu_options);
      if (global.births_deaths_UNWPP) await births_deaths_UNWPP.processRasters(births_deaths_unwpp_options);
      if (global.births_deaths_HMD) await births_deaths_HMD.processRasters(births_deaths_hmd_options);
      if (global.births_deaths_OLS) await births_deaths_OLS.processRasters(births_deaths_ols_options);
    }
    
    /**
     * Step J: Models labour force participation rates (LFPR) and sector employment breakdowns (agriculture, industry, services).
     * @alias NWM.J_processProfessions
     * 
     * @param {Object} [arg0_options]
     *  @param {Object} [arg0_options.lfpr_ilo]
     *  @param {Object} [arg0_options.lfpr_olivetti]
     *  @param {Object} [arg0_options.lfpr_ols]
     *  @param {Object} [arg0_options.professions]
     *  @param {Object} [arg0_options.professions_ilo]
     *  @param {Object} [arg0_options.professions_olivetti]
     *  @param {boolean} [arg0_options.skip_training=false]
     *  @param {boolean} [arg0_options.use_existing_models=false]
     */
    static async J_processProfessions (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Declare local instance variables
      let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
      let skip_training = (options.skip_training || options.use_existing_models || options.train === false);
      
      let lfpr_ilo_options = { overwrite: overwrite, ...(options.lfpr_ilo || {}) };
      let lfpr_olivetti_options = { overwrite: overwrite, ...(options.lfpr_olivetti || {}) };
      let lfpr_ols_options = { overwrite: overwrite, skip_training: skip_training, ...(options.lfpr_ols || {}) };
      let professions_ilo_options = { overwrite: overwrite, ...(options.professions_ilo || {}) };
      let professions_olivetti_options = { overwrite: overwrite, ...(options.professions_olivetti || {}) };
      let professions_options = { overwrite: overwrite, ...(options.professions || {}) };
      
      if (skip_training) {
        if (!professions_options.exclude) professions_options.exclude = [];
        if (!professions_options.exclude.includes("B")) professions_options.exclude.push("B");
        if (!professions_options.exclude.includes("C")) professions_options.exclude.push("C");
        professions_options.skip_training = true;
        console.log(`[NWM] Step J: Skipping Professions Multinomial Logit training (using existing models).`);
      }
      
      //Function body
      console.log(`[NWM] === Step J: Processing Labour Force & Professions ===`);
      if (global.LFPR_ILO) await LFPR_ILO.processRasters(lfpr_ilo_options);
      if (global.LFPR_Olivetti) await LFPR_Olivetti.processRasters(lfpr_olivetti_options);
      if (global.LFPR_OLS) await LFPR_OLS.processRasters(lfpr_ols_options);
      
      if (global.professions_ILO) await professions_ILO.processRasters(professions_ilo_options);
      if (global.professions_Olivetti) await professions_Olivetti.processRasters(professions_olivetti_options);
      if (global.professions) await professions.processRasters(professions_options);
    }
    
    /**
     * Master orchestrator for the National / World Model (NWM) demographic and economic pipeline.
     * Executes all sub-pipelines sequentially or filters by exclusion / stage selection.
     * @alias NWM.processRasters
     * 
     * @param {Object} [arg0_options]
     *  @param {Array<string>} [arg0_options.exclude] - Step letters or stage names to skip e.g. ["A", "C", "stadester"]
     *  @param {boolean} [arg0_options.skip_training=false] - If true, skips regression/model training and reuses existing models.
     *  @param {Array<string>} [arg0_options.stages] - Specific steps or stage names to execute exclusively
     *  @param {boolean} [arg0_options.use_existing_models=false] - Alias for skip_training.
     */
    static async processRasters (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Initialise options
      if (!options.exclude) options.exclude = [];
      if (options.overwrite === undefined) options.overwrite = true;
      if (options.use_existing_models) options.skip_training = true;
      
      //Declare local instance variables
      let should_run = function (step_letter, stage_name) {
        if (options.exclude && options.exclude.includes(step_letter)) return false;
        if (options.exclude && options.exclude.includes(stage_name)) return false;
        if (options.stages && Array.isArray(options.stages))
          return options.stages.includes(step_letter) || options.stages.includes(stage_name);
        return true;
      };
      
      //Function body
      console.log(`[NWM] Launching Master NWM Pipeline${options.skip_training ? " (Skip Training / Reusing Existing Models)" : ""}...`);
      this.loadDependencies(options);
      
      if (should_run("A", "substrata")) await this.A_processSubstrata(options);
      if (should_run("B", "stadester")) await this.B_processStadester(options);
      if (should_run("C", "eoscala_gdp")) await this.C_processEoscalaGDP(options);
      if (should_run("D", "gdp_pc")) await this.D_processGDPPerCapita(options);
      if (should_run("E", "covariates")) await this.E_processCovariates(options);
      if (should_run("F", "gini")) await this.F_processGini(options);
      if (should_run("G", "wealth_income")) await this.G_processWealthIncome(options);
      if (should_run("H", "age_sex")) await this.H_processAgeSex(options);
      if (should_run("I", "births_deaths")) await this.I_processBirthsDeaths(options);
      if (should_run("J", "professions")) await this.J_processProfessions(options);
      
      console.log(`[NWM] Successfully completed Master NWM Pipeline.`);
    }
  };
}
