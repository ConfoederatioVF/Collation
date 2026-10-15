//Initialise functions
{
  
  /**
   * Unified Econometric Downscaling Engine for Historical GDP and GDP Per Capita.
   * Follows the Maddison, MPD, Nordhaus (G-Econ), and De Long methodology:
   * 1. Intensive productivity (Per-Capita GDP) is predicted and calibrated first.
   * 2. Extensive output (Total GDP) aggregates strictly downstream: Total = PerCapita * Population.
   * 
   * @class Eoscala_GDP
   */
  global.Eoscala_GDP = class {
    static input_covariates_obj = () => {
      let covariates_obj = {
        ...GDP_PPP_SEDAC.covariates_obj,
        "rurc_": (y) => [`${population_Stadester.input_rurc_folder}/stadester_rural_${y}.png`, "float32"],
        "urbc_": (y) => [`${population_Stadester.input_urbc_folder}/stadester_urban_${y}.png`, "float32"]
      };
      delete covariates_obj["uopp_"];
      delete covariates_obj["popd_"];
      
      //Return statement
      return covariates_obj;
    };
    
    /**
     * Step A: Generates initial uniform historical per-capita target rasters from national targets.
     * Assigns national per-capita GDP (Target / National_Pop) to populated pixels.
     * @alias Eoscala_GDP.A_generateGDP_pcRasters
     * 
     * @param {Object} [arg0_options]
     *  @param {number} [arg0_options.concurrency=8]
     *  @param {boolean} [arg0_options.overwrite=true]
     * @returns {Promise<Array>}
     */
    static async A_generateGDP_pcRasters (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Declare local instance variables
      let geocode_obj = admin_modern.getISO3ColourcodesObject();
      let geocodes_raster_path = admin_modern.input_geocodes_raster;
      let gdp_obj = this.getGDPObject();
      let hyde_years = (options.years) ? options.years : landuse_HYDE.sorted_hyde_years;
      let out_dir = (typeof path !== "undefined") ? path.resolve(this.input_gdp_pc_folder) : this.input_gdp_pc_folder;
      let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
      let target_years = [];
      
      if (!fs.existsSync(out_dir)) fs.mkdirSync(out_dir, { recursive: true });
      
      for (let i = 0; i < hyde_years.length; i++) {
        let local_output_path = `${this.input_gdp_pc_folder}${this.pc_prefix}_${hyde_years[i]}.png`;
        let local_popc_path = `${population_Stadester.input_popc_folder}stadester_population_${hyde_years[i]}.png`;
        
        if (fs.existsSync(local_popc_path))
          if (overwrite || !fs.existsSync(local_output_path))
            target_years.push(hyde_years[i]);
      }
      
      if (target_years.length === 0) return [];
      
      //Return statement
      return GeoPNG.processTimeseriesParallel({
        concurrency: options.concurrency || 8,
        items: target_years,
        name: `${this.pc_prefix} A_generateGDP_pcRasters (Uniform Historical Target)`,
        handler: async (year) => {
          let geocode_raster = GeoPNG.loadImage(geocodes_raster_path);
          let local_output_path = `${this.input_gdp_pc_folder}${this.pc_prefix}_${year}.png`;
          let local_popc_path = `${population_Stadester.input_popc_folder}stadester_population_${year}.png`;
          let local_popc_raster = GeoPNG.loadNumberRasterImage(local_popc_path, { format: "float32" });
          let national_pop_sums = {};
          
          //1. Calculate national populations and global average
          let world_gdp = 0;
          let world_pop = 0;
          
          for (let local_index = 0; local_index < local_popc_raster.data.length; local_index++) {
            let local_pop = local_popc_raster.data[local_index];
            if (local_pop > 0) {
              let byte_index = local_index * 4;
              let local_colour_key = `${geocode_raster.data[byte_index]},${geocode_raster.data[byte_index+1]},${geocode_raster.data[byte_index+2]}`;
              let local_geocodes = geocode_obj[local_colour_key];
              
              if (local_geocodes)
                for (let x = 0; x < local_geocodes.length; x++)
                  Object.modifyValue(national_pop_sums, local_geocodes[x], local_pop);
            }
          }
          
          for (let code of Object.keys(gdp_obj)) {
            let g = gdp_obj[code]?.[year];
            let p = national_pop_sums[code];
            if (g && p > 0) {
              world_gdp += g;
              world_pop += p;
            }
          }
          let delong_hg_base = this.getDelongBaseline(year);
          let global_avg_pc = (world_pop > 0) ? Math.max(delong_hg_base, world_gdp / world_pop) : delong_hg_base;
          
          //2. Assign uniform per-capita figures (intensive initialisation)
          GeoPNG.saveNumberRasterImage({
            file_path: local_output_path,
            format: "float32",
            height: 2160,
            width: 4320,
            function: (local_index) => {
              let local_pop = local_popc_raster.data[local_index];
              
              if (local_pop >= 1.0) {
                let byte_index = local_index * 4;
                let local_colour_key = `${geocode_raster.data[byte_index]},${geocode_raster.data[byte_index+1]},${geocode_raster.data[byte_index+2]}`;
                let local_geocodes = geocode_obj[local_colour_key];
                
                if (local_geocodes && local_geocodes.length > 0) {
                  let primary_code = local_geocodes[0];
                  let target_gdp = gdp_obj[primary_code]?.[year];
                  let target_pop = national_pop_sums[primary_code];
                  
                  if (target_gdp && target_pop > 0) {
                    return Math.max(delong_hg_base, target_gdp / target_pop);
                  } else {
                    return global_avg_pc;
                  }
                }
              }
              return 0;
            }
          });
        }
      });
    }
    
    /**
     * Loads regression covariates for a given year.
     * @alias Eoscala_GDP.B_loadCovariates
     * 
     * @param {number|string} arg0_year
     * @returns {Promise<Object>}
     */
    static async B_loadCovariates (arg0_year) {
      //Convert from parameters
      let year = arg0_year;
      
      //Declare local instance variables
      let input_file_path = `${this.input_gdp_pc_folder}${this.pc_prefix}_${year}.png`;
      
      //Return statement
      return Statistics.loadOLSCovariates(input_file_path, {
        utility_format: "float32",
        covariates_obj: this.input_covariates_obj(),
        formatting_parameters: [year]
      });
    }
    
    /**
     * Trains a single year OLS model in per-capita space.
     * @alias Eoscala_GDP.B_trainGDP_pcModel
     * 
     * @param {number|string} arg0_year
     * @param {Object} [arg1_options]
     * @returns {Promise<Object>}
     */
    static async B_trainGDP_pcModel (arg0_year, arg1_options) {
      //Convert from parameters
      let year = parseInt(arg0_year);
      let options = (arg1_options) ? arg1_options : {};
      
      //Initialise options
      if (!options.key) options.key = year.toString();
      if (!options.lambda) options.lambda = 1e6;
      
      //Declare local instance variables
      let covariates_obj = await this.B_loadCovariates(year);
      let output_file_path = `${this.intermediate_ols_folder}OLS_${this.pc_prefix}_${year}.json`;
      
      //Return statement
      return Statistics.trainOLSModel(output_file_path, covariates_obj, options);
    }
    
    /**
     * Step B: Trains spatial regression models across all HYDE years predicting per-capita GDP.
     * @alias Eoscala_GDP.B_trainGDP_pcModels
     * 
     * @param {Object} [arg0_options]
     *  @param {number} [arg0_options.concurrency=8]
     * @returns {Promise<void>}
     */
    static async B_trainGDP_pcModels (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Declare local instance variables
      let invalid_years = [];
      let years = (options.years) ? options.years : landuse_HYDE.sorted_hyde_years;
      
      if (!fs.existsSync(this.intermediate_ols_folder))
        fs.mkdirSync(this.intermediate_ols_folder, { recursive: true });
      
      //1. Train models in parallel
      await Statistics.trainOLSModelsParallel(years, (year) => {
        let cov_obj = this.input_covariates_obj();
        let covariates_map = {};
        let keys = Object.keys(cov_obj);
        for (let x = 0; x < keys.length; x++) {
          let k = keys[x];
          covariates_map[k] = cov_obj[k](year);
        }
        
        return {
          covariates_map: covariates_map,
          options: {
            ...options,
            key: year.toString(),
            lambda: Math.returnSafeNumber(options.lambda, 1e6)
          },
          output_file_path: `${this.intermediate_ols_folder}OLS_${this.pc_prefix}_${year}.json`,
          target_file_path: `${this.input_gdp_pc_folder}${this.pc_prefix}_${year}.png`,
          target_format: "float32"
        };
      }, {
        concurrency: options.concurrency || 8,
        name: `${this.pc_prefix} 2nd-pass OLS Training`
      });
      
      //2. Identify invalid models (all coefficients are 0)
      for (let i = 0; i < years.length; i++) {
        let file_path = `${this.intermediate_ols_folder}OLS_${this.pc_prefix}_${years[i]}.json`;
        if (fs.existsSync(file_path)) {
          let model_data = JSON.parse(fs.readFileSync(file_path, "utf8"));
          let sum_coeffs = 0;
          for (let key in model_data.coefficients)
            sum_coeffs += Math.abs(model_data.coefficients[key]);
          if (sum_coeffs === 0) {
            invalid_years.push(years[i]);
            fs.renameSync(file_path, `${this.intermediate_ols_folder}INVALID_OLS_${this.pc_prefix}_${years[i]}.json`);
          }
        }
      }
      
      //3. Compute geometric average of valid OLS models
      let geomean_data = await Statistics.geomeanOLSModels(this.intermediate_ols_folder, `OLS_${this.pc_prefix}_`);
      
      //4. Restore and overwrite invalid models with the geomean
      for (let i = 0; i < invalid_years.length; i++) {
        let invalid_path = `${this.intermediate_ols_folder}INVALID_OLS_${this.pc_prefix}_${invalid_years[i]}.json`;
        let target_path = `${this.intermediate_ols_folder}OLS_${this.pc_prefix}_${invalid_years[i]}.json`;
        
        if (fs.existsSync(invalid_path)) {
          let invalid_data = JSON.parse(fs.readFileSync(invalid_path, "utf8"));
          invalid_data.coefficients = geomean_data.coefficients;
          fs.writeFileSync(target_path, JSON.stringify(invalid_data, null, 2));
          fs.unlinkSync(invalid_path);
        }
      }
    }
    
    /**
     * Step C: Generates continuous spatial per-capita GDP prediction rasters.
     * Incorporates urban wage/productivity premium and agricultural productivity.
     * @alias Eoscala_GDP.C_generateOLS_GDP_pcRasters
     * 
     * @param {Object} [arg0_options]
     *  @param {number} [arg0_options.concurrency=8]
     *  @param {boolean} [arg0_options.overwrite=true]
     * @returns {Promise<Array>}
     */
    static async C_generateOLS_GDP_pcRasters (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Declare local instance variables
      let hyde_years = (options.years) ? options.years : landuse_HYDE.sorted_hyde_years;
      let out_dir = (typeof path !== "undefined") ? path.resolve(this.intermediate_ols_rasters_folder) : this.intermediate_ols_rasters_folder;
      let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
      let target_years = [];
      
      if (!fs.existsSync(out_dir)) fs.mkdirSync(out_dir, { recursive: true });
      
      for (let i = 0; i < hyde_years.length; i++) {
        let local_input_path = `${this.intermediate_ols_folder}OLS_${this.pc_prefix}_${hyde_years[i]}.json`;
        let local_output_path = `${this.intermediate_ols_rasters_folder}OLS_${this.pc_prefix}_${hyde_years[i]}.png`;
        if (fs.existsSync(local_input_path) && (overwrite || !fs.existsSync(local_output_path)))
          target_years.push(hyde_years[i]);
      }
      
      if (target_years.length === 0) return [];
      
      //Return statement
      return Statistics.generateOLSRastersParallel(target_years, (year) => {
        let cov_obj = this.input_covariates_obj();
        let covariates_map = {};
        let keys = Object.keys(cov_obj);
        for (let x = 0; x < keys.length; x++) {
          let k = keys[x];
          covariates_map[k] = cov_obj[k](year);
        }
        
        return {
          covariates_map: covariates_map,
          model_obj: `${this.intermediate_ols_folder}OLS_${this.pc_prefix}_${year}.json`,
          options: { format: "float32" },
          output_file_path: `${this.intermediate_ols_rasters_folder}OLS_${this.pc_prefix}_${year}.png`
        };
      }, {
        concurrency: options.concurrency || 8,
        name: `${this.pc_prefix} OLS Raster Generation (Per-Capita Prediction)`
      });
    }
    
    /**
     * Step D: Normalises predicted per-capita rasters against the first pass with regularised log tails.
     * Operates strictly in per-capita ($/person) space.
     * @alias Eoscala_GDP.D_normaliseGDP_pcRasters
     * 
     * @param {Object} [arg0_options]
     *  @param {number} [arg0_options.concurrency=8]
     * @returns {Promise<void>}
     */
    static async D_normaliseGDP_pcRasters (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Declare local instance variables
      let global_prev_max = 0;
      let landarea_file = metadata_HYDE.input_raster_land_area;
      let landarea_raster = GeoPNG.loadNumberRasterImage(landarea_file, { format: "int32" });
      let out_dir = (typeof path !== "undefined") ? path.resolve(this.intermediate_pc_estimates_folder) : this.intermediate_pc_estimates_folder;
      let thresholds = {};
      let years = (options.years) ? options.years : landuse_HYDE.sorted_hyde_years;
      
      if (!fs.existsSync(out_dir)) fs.mkdirSync(out_dir, { recursive: true });
      
      //1. Fast sequential pre-pass to calculate limits
      let final_year = years[years.length - 1];
      let first_pass_path = `${this.input_gdp_pc_folder}${this.pc_prefix}_${final_year}.png`;
      
      if (fs.existsSync(first_pass_path)) {
        let final_max = -Infinity;
        let first_pass_raster = GeoPNG.loadNumberRasterImage(first_pass_path, { format: "float32" });
        for (let x = 0; x < first_pass_raster.data.length; x++) {
          let fp_val = first_pass_raster.data[x];
          if (isFinite(fp_val) && fp_val > final_max) final_max = fp_val;
        }
        if (isFinite(final_max) && final_max > 0) global_prev_max = final_max;
      }
      
      for (let i = 0; i < years.length; i++)
        thresholds[years[i]] = (global_prev_max > 0) ? global_prev_max : 5000000;
      
      //2. Parallel raster normalisation
      await GeoPNG.processTimeseriesParallel({
        concurrency: options.concurrency || 8,
        items: years,
        name: `${this.pc_prefix} D_normaliseGDP_pcRasters`,
        handler: async (year) => {
          if (!thresholds[year]) return null;
          let prev_max = thresholds[years[Math.max(0, years.indexOf(year) - 1)]] || 0;
          
          let first_pass_path = `${this.input_gdp_pc_folder}${this.pc_prefix}_${year}.png`;
          let second_pass_path = `${this.intermediate_ols_rasters_folder}OLS_${this.pc_prefix}_${year}.png`;
          let pop_path = `${population_Stadester.input_popc_folder}stadester_population_${year}.png`;
          let output_path = `${this.intermediate_pc_estimates_folder}${this.pc_prefix}_${year}.png`;
          
          let first_pass_raster = GeoPNG.loadNumberRasterImage(first_pass_path, { format: "float32" });
          let second_pass_raster = GeoPNG.loadNumberRasterImage(second_pass_path, { format: "float32" });
          let pop_raster = GeoPNG.loadNumberRasterImage(pop_path, { format: "float32" });
          
          //Tukey's fences with log-tail normalisation
          let regularised_pc = GeoPNG.regulariseLogTail({
            allow_zero_or_negative: false,
            data: second_pass_raster.data,
            valid_filter: (x) => landarea_raster.data[x] > 0 && pop_raster.data[x] >= 1.0
          });
          
          GeoPNG.saveNumberRasterImage({
            file_path: output_path,
            format: "float32",
            height: 2160,
            width: 4320,
            function: (local_index) => {
              if (landarea_raster.data[local_index] === 0 || pop_raster.data[local_index] < 1.0) return 0;
              let pc_val = regularised_pc[local_index];
              return (isFinite(pc_val) && pc_val > 0 && pc_val < 3.402823466e38) ? pc_val : 0;
            }
          });
        }
      });
    }
    
    /**
     * Step E: Integrates SEDAC per-capita baseline in PER-CAPITA space.
     * Evaluates intensive per-capita surfaces:
     * - 1990-2022: Uses empirical SEDAC per capita (SEDAC_Total / Pop).
     * - 1800-1990: Blends modelled per-capita surface into 1990 SEDAC per capita.
     * - Pre-1800: Modelled per-capita surface is directly preserved.
     * @alias Eoscala_GDP.E_generateGDPRasters
     * 
     * @param {Object} [arg0_options]
     *  @param {number} [arg0_options.concurrency=8]
     *  @param {boolean} [arg0_options.overwrite=true]
     * @returns {Promise<void>}
     */
    static async E_generateGDPRasters (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Declare local instance variables
      let hyde_years = (options.years) ? options.years : landuse_HYDE.sorted_hyde_years;
      let out_dir = (typeof path !== "undefined") ? path.resolve(this.intermediate_gdp_interpolated) : this.intermediate_gdp_interpolated;
      let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
      let sedac_domain = [1800, 1990];
      let sedac1_domain = [1800, 1950];
      let sedac2_domain = [1950, 1990];
      let target_years = [];
      let template_path = `${this.sedac_class().bf}${this.prefix}_2022.png`;
      let template_sum = 0;
      if (fs.existsSync(template_path))
        template_sum = GeoPNG.getImageSum(template_path, { format: "float32" });
      let to_path = `${this.sedac_class().bf}${this.prefix}_1990.png`;
      let world_gdp_obj = this.getWorldGDPObject();
      let year_gap = sedac_domain[1] - sedac_domain[0];
      let year_gap2 = sedac2_domain[1] - sedac2_domain[0];
      
      if (!fs.existsSync(out_dir)) fs.mkdirSync(out_dir, { recursive: true });
      
      for (let i = 0; i < hyde_years.length; i++) {
        let local_output_path = `${this.intermediate_gdp_interpolated}${this.prefix}_${hyde_years[i]}.png`;
        if (overwrite || !fs.existsSync(local_output_path))
          target_years.push(hyde_years[i]);
      }
      
      if (target_years.length === 0) return;
      
      //Return statement
      return GeoPNG.processTimeseriesParallel({
        concurrency: options.concurrency || 8,
        items: target_years,
        name: `${this.prefix} Step E: SEDAC Historical Blending`,
        handler: async (current_year) => {
          let local_output_path = `${this.intermediate_gdp_interpolated}${this.prefix}_${current_year}.png`;
          let pop_path = `${population_Stadester.input_popc_folder}stadester_population_${current_year}.png`;
          let pop_raster = (fs.existsSync(pop_path)) ?
            GeoPNG.loadNumberRasterImage(pop_path, { format: "float32" }) : null;
          
          //1. Empirical SEDAC era (1990-2022): compute empirical per capita (SEDAC_Total / Pop)
          if (current_year >= 1990 && current_year <= 2022) {
            let local_sedac_path = `${this.sedac_class().bf}${this.prefix}_${current_year}.png`;
            if (fs.existsSync(local_sedac_path) && pop_raster) {
              let sedac_raster = GeoPNG.loadNumberRasterImage(local_sedac_path, { format: "float32" });
              GeoPNG.saveNumberRasterImage({
                file_path: local_output_path,
                format: "float32",
                height: 2160,
                width: 4320,
                function: (local_index) => {
                  let p = pop_raster.data[local_index];
                  if (p < 1.0) return 0;
                  let tot = sedac_raster.data[local_index];
                  return (isFinite(tot) && tot > 0) ? (tot / p) : 0;
                }
              });
              return;
            }
          }
          
          //2. Post-2022: scale SEDAC 2022 per-capita by world per-capita growth
          if (current_year > 2022) {
            let pop_2022_path = `${population_Stadester.input_popc_folder}stadester_population_2022.png`;
            if (fs.existsSync(template_path) && fs.existsSync(pop_2022_path) && pop_raster) {
              let target_global = Math.returnSafeNumber(world_gdp_obj[current_year], template_sum);
              let global_scalar = (template_sum > 0) ? target_global / template_sum : 1;
              let template_raster = GeoPNG.loadNumberRasterImage(template_path, { format: "float32" });
              let pop_2022_raster = GeoPNG.loadNumberRasterImage(pop_2022_path, { format: "float32" });
              
              GeoPNG.saveNumberRasterImage({
                file_path: local_output_path,
                format: "float32",
                height: 2160,
                width: 4320,
                function: (local_index) => {
                  let p_2022 = pop_2022_raster.data[local_index];
                  if (p_2022 < 1.0) return 0;
                  let base_pc = template_raster.data[local_index] / p_2022;
                  return base_pc * global_scalar;
                }
              });
              return;
            }
          }
          
          //3. Pre-1990: derive from normalised modelled per capita
          let pc_path = `${this.intermediate_pc_estimates_folder}${this.pc_prefix}_${current_year}.png`;
          if (!fs.existsSync(pc_path)) return;
          let pc_raster = GeoPNG.loadNumberRasterImage(pc_path, { format: "float32" });
          
          if (current_year < sedac_domain[0]) {
            //Pre-1800: preserve modelled per capita directly in per-capita space
            GeoPNG.saveNumberRasterImage({
              file_path: local_output_path,
              format: "float32",
              height: 2160,
              width: 4320,
              function: (local_index) => {
                let pc = pc_raster.data[local_index];
                let p = (pop_raster) ? pop_raster.data[local_index] : 0;
                return (p >= 1.0 && isFinite(pc) && pc > 0) ? pc : 0;
              }
            });
          } else {
            //1800 <= current_year < 1990: blend modelled per capita into SEDAC 1990 per capita in per-capita space
            let fraction = (current_year - sedac_domain[0]) / year_gap;
            let is_early = (current_year < sedac1_domain[1]);
            let pop_1990_path = `${population_Stadester.input_popc_folder}stadester_population_1990.png`;
            let pop_1990_raster = (fs.existsSync(pop_1990_path)) ?
              GeoPNG.loadNumberRasterImage(pop_1990_path, { format: "float32" }) : null;
            let threshold_fraction = (!is_early) ? (current_year - sedac2_domain[0]) / year_gap2 : 0;
            let to_raster = GeoPNG.loadNumberRasterImage(to_path, { format: "float32" });
            
            GeoPNG.saveNumberRasterImage({
              file_path: local_output_path,
              format: "float32",
              height: 2160,
              width: 4320,
              function: (local_index) => {
                let from_pc = pc_raster.data[local_index];
                let p_1990 = (pop_1990_raster) ? pop_1990_raster.data[local_index] : 1;
                let to_pc = (p_1990 >= 1.0) ? to_raster.data[local_index] / p_1990 : 0;
                
                if (is_early) {
                  return from_pc + (to_pc - from_pc) * fraction;
                } else {
                  let effective_fraction = fraction * (1 - threshold_fraction) + threshold_fraction;
                  return from_pc + (to_pc - from_pc) * effective_fraction;
                }
              }
            });
          }
        }
      });
    }
    
    /**
     * Legacy Step F: Global scaling facade for backward compatibility.
     * @alias Eoscala_GDP.F_scaleGDPRastersToGlobal
     */
    static async F_scaleGDPRastersToGlobal (arg0_options) {
      //No-op; intensive scaling is handled within the unified per-capita pipeline
      return;
    }
    
    /**
     * Legacy Step G: SEDAC interpolation facade for backward compatibility.
     * @alias Eoscala_GDP.G_interpolateToSEDAC
     */
    static async G_interpolateToSEDAC (arg0_options) {
      //No-op; intensive SEDAC blending is handled within Step E
      return;
    }
    
    /**
     * Returns the De Long subsistence baseline per capita for the current mode and year.
     * Evaluates from DeLong ex-Nordhaus series (delong_gdp_pc.csv) converted to 2000$.
     * 
     * @param {number|string} [arg0_year=-10000]
     * @returns {number}
     */
    static getDelongBaseline (arg0_year) {
      //Convert from parameters
      let year = (arg0_year !== undefined) ? parseInt(arg0_year) : -10000;
      
      //Return statement
      if (this.mode === "nominal") {
        return (typeof GDP_nominal !== "undefined" && GDP_nominal.getDelongBaseline) ?
          GDP_nominal.getDelongBaseline(year) : undefined;
      } else {
        return (typeof GDP_PPP !== "undefined" && GDP_PPP.getDelongBaseline) ?
          GDP_PPP.getDelongBaseline(year) : undefined;
      }
    }
    
    /**
     * Returns the De Long physical subsistence floor per capita for a given year.
     * @alias Eoscala_GDP.getDelongSubsistenceBaseline
     * 
     * @param {number|string} [arg0_year=-10000]
     * @returns {number}
     */
    static getDelongSubsistenceBaseline (arg0_year) {
      //Convert from parameters
      let year = (arg0_year !== undefined) ? parseInt(arg0_year) : -10000;
      
      //Return statement
      if (this.mode === "nominal") {
        return (typeof GDP_nominal !== "undefined" && GDP_nominal.getDelongSubsistenceBaseline) ?
          GDP_nominal.getDelongSubsistenceBaseline(year) : undefined;
      } else {
        return (typeof GDP_PPP !== "undefined" && GDP_PPP.getDelongSubsistenceBaseline) ?
          GDP_PPP.getDelongSubsistenceBaseline(year) : undefined;
      }
    }
    
    /**
     * Step H: Calibrates Per-Capita GDP to national Maddison benchmarks FIRST,
     * preserving intra-national spatial heterogeneity, urban productivity premiums, and dasymetric structure.
     * Downstream, Total GDP is computed as extensive aggregate: Total = PerCapita * Population.
     * @alias Eoscala_GDP.H_scaleGDPRastersToNational
     * 
     * @param {Object} [arg0_options]
     *  @param {number} [arg0_options.concurrency=8]
     *  @param {boolean} [arg0_options.overwrite=true]
     * @returns {Promise<void>}
     */
    static async H_scaleGDPRastersToNational (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Declare local instance variables
      let geocode_obj = admin_modern.getISO3ColourcodesObject();
      let geocode_raster = GeoPNG.loadImage(admin_modern.input_geocodes_raster);
      let gdp_national_obj = this.getGDPObject();
      let hyde_years = (options.years) ? options.years : landuse_HYDE.sorted_hyde_years;
      let out_dir_national = (typeof path !== "undefined") ? path.resolve(this.intermediate_gdp_scaled_to_national) : this.intermediate_gdp_scaled_to_national;
      let out_dir_pc = (typeof path !== "undefined") ? path.resolve(this.output_gdp_pc_folder) : this.output_gdp_pc_folder;
      let previous_max_pc = 0;
      let thresholds = {};
      
      if (!fs.existsSync(out_dir_national)) fs.mkdirSync(out_dir_national, { recursive: true });
      if (!fs.existsSync(out_dir_pc)) fs.mkdirSync(out_dir_pc, { recursive: true });
      
      //1. Fast sequential pre-pass for thresholds and country calibration scalars in per-capita space
      for (let i = 0; i < hyde_years.length; i++) {
        let current_year = hyde_years[i];
        let local_input_file_path = (current_year < 1990 && fs.existsSync(`${this.intermediate_pc_estimates_folder}${this.pc_prefix}_${current_year}.png`)) ?
          `${this.intermediate_pc_estimates_folder}${this.pc_prefix}_${current_year}.png` :
          `${this.intermediate_gdp_interpolated}${this.prefix}_${current_year}.png`;
        if (!fs.existsSync(local_input_file_path))
          local_input_file_path = `${this.intermediate_pc_estimates_folder}${this.pc_prefix}_${current_year}.png`;
        if (!fs.existsSync(local_input_file_path)) continue;
        
        let local_input_raster = GeoPNG.loadNumberRasterImage(local_input_file_path, { format: "float32" });
        let local_popc_file_path = `${population_Stadester.input_popc_folder}stadester_population_${current_year}.png`;
        let local_popc_raster = GeoPNG.loadNumberRasterImage(local_popc_file_path, { format: "float32" });
        let local_urbc_file_path = `${population_Stadester.input_urbc_folder}stadester_urban_${current_year}.png`;
        let local_urbc_raster = (fs.existsSync(local_urbc_file_path)) ?
          GeoPNG.loadNumberRasterImage(local_urbc_file_path, { format: "float32" }) : null;
        
        let country_stats = {};
        let current_max_pc = 0;
        let delong_hg_base = this.getDelongBaseline(-10000);
        let delong_world_base = this.getDelongBaseline(current_year);
        let is_total_raster = local_input_file_path.includes(this.prefix + "_") && !local_input_file_path.includes(this.pc_prefix + "_") && !local_input_file_path.includes("interpolated");
        let local_delta_sums = {};
        let local_min_ols = {};
        let local_pop_sums = {};
        let local_threshold = (previous_max_pc > 0) ? Math.min(previous_max_pc * 4, 500000) : 500000;
        let clamp_alpha = local_threshold * 0.1;
        
        //Calculate national population and minimum OLS estimate per country
        for (let x = 0; x < local_input_raster.data.length; x++) {
          let p = local_popc_raster.data[x];
          if (p >= 1.0) {
            let byte_index = x * 4;
            let local_colour_key = `${geocode_raster.data[byte_index]},${geocode_raster.data[byte_index+1]},${geocode_raster.data[byte_index+2]}`;
            let local_geocodes = geocode_obj[local_colour_key];
            if (local_geocodes && local_geocodes.length > 0) {
              let primary_code = local_geocodes[0];
              let local_pc = is_total_raster ? (local_input_raster.data[x] / p) : local_input_raster.data[x];
              Object.modifyValue(local_pop_sums, primary_code, p);
              if (local_pc > 0) {
                if (local_min_ols[primary_code] === undefined || local_pc < local_min_ols[primary_code])
                  local_min_ols[primary_code] = local_pc;
              }
            }
          }
        }
        
        //Calculate population-weighted OLS delta sums per country
        for (let x = 0; x < local_input_raster.data.length; x++) {
          let p = local_popc_raster.data[x];
          if (p >= 1.0) {
            let byte_index = x * 4;
            let local_colour_key = `${geocode_raster.data[byte_index]},${geocode_raster.data[byte_index+1]},${geocode_raster.data[byte_index+2]}`;
            let local_geocodes = geocode_obj[local_colour_key];
            if (local_geocodes && local_geocodes.length > 0) {
              let primary_code = local_geocodes[0];
              let local_pc = is_total_raster ? (local_input_raster.data[x] / p) : local_input_raster.data[x];
              let min_base = (local_min_ols[primary_code] !== undefined) ? local_min_ols[primary_code] : 0;
              let delta = Math.max(0, local_pc - min_base);
              Object.modifyValue(local_delta_sums, primary_code, delta * p);
            }
          }
        }
        
        //Calibrate per-capita surplus and statistics per country
        Object.iterate(local_pop_sums, (local_key, pop_c) => {
          let delta_mean = (pop_c > 0 && local_delta_sums[local_key] > 0) ? (local_delta_sums[local_key] / pop_c) : 0;
          let local_target_total = gdp_national_obj[local_key]?.[current_year];
          let min_ols = (local_min_ols[local_key] !== undefined) ? local_min_ols[local_key] : 0;
          let target_pc = (local_target_total && pop_c > 0) ? (local_target_total / pop_c) : delong_world_base;
          let country_floor = Math.min(target_pc * 0.5, delong_world_base * 0.5);
          let surplus_pc = Math.max(0, target_pc - country_floor);
          
          country_stats[local_key] = {
            delong_base: country_floor,
            delta_mean: delta_mean,
            min_ols: min_ols,
            pop: pop_c,
            surplus_pc: surplus_pc,
            target_pc: target_pc
          };
        });
        
        //Determine current_max_pc
        for (let x = 0; x < local_input_raster.data.length; x++) {
          let p = local_popc_raster.data[x];
          if (p >= 1.0) {
            let local_pc = is_total_raster ? (local_input_raster.data[x] / p) : local_input_raster.data[x];
            let byte_index = x * 4;
            let local_colour_key = `${geocode_raster.data[byte_index]},${geocode_raster.data[byte_index+1]},${geocode_raster.data[byte_index+2]}`;
            let local_geocodes = geocode_obj[local_colour_key];
            
            let final_pc = local_pc;
            if (local_geocodes && local_geocodes.length > 0) {
              let stats = country_stats[local_geocodes[0]];
              if (stats) {
                let delta = Math.max(0, local_pc - stats.min_ols);
                let mult = (stats.delta_mean > 0) ? (delta / stats.delta_mean) : 1.0;
                let cell_pc = stats.delong_base + stats.surplus_pc * mult;
                if (cell_pc > local_threshold)
                  cell_pc = local_threshold + clamp_alpha * Math.log(1 + ((cell_pc - local_threshold) / clamp_alpha));
                final_pc = cell_pc;
              }
            }
            if (isFinite(final_pc) && final_pc > current_max_pc) current_max_pc = final_pc;
          }
        }
        
        if (current_max_pc > 0) previous_max_pc = current_max_pc;
        thresholds[current_year] = { max: current_max_pc, stats: country_stats, threshold: local_threshold };
      }
      
      //2. Parallel raster generation: PER-CAPITA PREDICTED FIRST, TOTAL AGGREGATED DOWNSTREAM
      await GeoPNG.processTimeseriesParallel({
        concurrency: options.concurrency || 8,
        items: hyde_years,
        name: `${this.pc_prefix} H_scaleGDPRastersToNational (Per-Capita First, Downstream Aggregation)`,
        handler: async (year) => {
          if (!thresholds[year]) return null;
          let stats = thresholds[year].stats;
          let threshold = thresholds[year].threshold;
          let local_input_file_path = (year < 1990 && fs.existsSync(`${this.intermediate_pc_estimates_folder}${this.pc_prefix}_${year}.png`)) ?
            `${this.intermediate_pc_estimates_folder}${this.pc_prefix}_${year}.png` :
            `${this.intermediate_gdp_interpolated}${this.prefix}_${year}.png`;
          if (!fs.existsSync(local_input_file_path))
            local_input_file_path = `${this.intermediate_pc_estimates_folder}${this.pc_prefix}_${year}.png`;
          let local_input_raster = GeoPNG.loadNumberRasterImage(local_input_file_path, { format: "float32" });
          let local_popc_file_path = `${population_Stadester.input_popc_folder}stadester_population_${year}.png`;
          let local_popc_raster = GeoPNG.loadNumberRasterImage(local_popc_file_path, { format: "float32" });
          let local_urbc_file_path = `${population_Stadester.input_urbc_folder}stadester_urban_${year}.png`;
          let local_urbc_raster = (fs.existsSync(local_urbc_file_path)) ?
            GeoPNG.loadNumberRasterImage(local_urbc_file_path, { format: "float32" }) : null;
          let local_output_pc = `${this.output_gdp_pc_folder}${this.pc_prefix}_${year}.png`;
          let local_output_total = `${this.intermediate_gdp_scaled_to_national}${this.prefix}_${year}.png`;
          let is_total_raster = local_input_file_path.includes(this.prefix + "_") && !local_input_file_path.includes(this.pc_prefix + "_") && !local_input_file_path.includes("interpolated");
          
          let clamp_alpha = threshold * 0.1;
          let delong_hg_base = this.getDelongBaseline(-10000);
          let min_cell_floor = delong_hg_base * 0.25;
          let raw_calibrated_pc = new Float32Array(4320 * 2160);
          
          //Calibrate per-capita GDP per cell using continuous OLS surplus allocation
          for (let local_index = 0; local_index < local_input_raster.data.length; local_index++) {
            let local_pop = local_popc_raster.data[local_index];
            if (local_pop < 1.0) continue;
            let local_pc = is_total_raster ? (local_input_raster.data[local_index] / local_pop) : local_input_raster.data[local_index];
            let byte_index = local_index * 4;
            let local_colour_key = `${geocode_raster.data[byte_index]},${geocode_raster.data[byte_index+1]},${geocode_raster.data[byte_index+2]}`;
            let local_geocodes = geocode_obj[local_colour_key];
            
            let cell_pc = local_pc;
            if (local_geocodes && local_geocodes.length > 0) {
              let primary_code = local_geocodes[0];
              let s = stats[primary_code];
              if (s) {
                let delta = Math.max(0, local_pc - s.min_ols);
                let mult = (s.delta_mean > 0) ? (delta / s.delta_mean) : 1.0;
                cell_pc = s.delong_base + s.surplus_pc * mult;
                if (cell_pc > threshold)
                  cell_pc = threshold + clamp_alpha * Math.log(1 + ((cell_pc - threshold) / clamp_alpha));
              } else {
                cell_pc = Math.max(min_cell_floor, local_pc);
              }
            } else {
              cell_pc = Math.max(min_cell_floor, local_pc);
            }
            raw_calibrated_pc[local_index] = Math.max(min_cell_floor, cell_pc);
          }
          
          let final_pc_data = raw_calibrated_pc;
          
          //For pre-industrial era (year < 1800): apply dasymetric blur only if explicitly enabled
          let blur_radius = (options.blur_radius !== undefined) ? options.blur_radius : 0;
          if (year < 1800 && blur_radius > 0) {
            let local_urbc_path = `${population_Stadester.input_urbc_folder}stadester_urban_${year}.png`;
            let local_urbc_raster = (fs.existsSync(local_urbc_path)) ?
              GeoPNG.loadNumberRasterImage(local_urbc_path, { format: "float32" }) : null;
            let blurred_pc = GeoPNG.dasymetricBlur({
              height: 2160,
              mask_data: geocode_raster.data,
              pop_data: local_popc_raster.data,
              radius: blur_radius,
              target_data: raw_calibrated_pc,
              width: 4320
            });
            final_pc_data = new Float32Array(4320 * 2160);
            for (let j = 0; j < 4320 * 2160; j++) {
              let is_urban = (local_urbc_raster && local_urbc_raster.data[j] > 0);
              let val = is_urban ? raw_calibrated_pc[j] : blurred_pc[j];
              final_pc_data[j] = Math.max(min_cell_floor, val);
            }
          }
          
          //PRIMARY EXPORT 1: Save Per-Capita GDP raster FIRST (preserving spatial heterogeneity)
          GeoPNG.saveNumberRasterImage({
            file_path: local_output_pc,
            format: "float32",
            height: 2160,
            width: 4320,
            function: (local_index) => {
              let local_pop = local_popc_raster.data[local_index];
              if (local_pop < 1.0) return 0;
              let pc_val = final_pc_data[local_index];
              return (isFinite(pc_val) && pc_val > 0 && pc_val < 3.402823466e38) ? Math.max(min_cell_floor, pc_val) : 0;
            }
          });
          
          //DOWNSTREAM EXPORT 2: Total GDP aggregates strictly downstream (Total = PerCapita * Population)
          GeoPNG.saveNumberRasterImage({
            file_path: local_output_total,
            format: "float32",
            height: 2160,
            width: 4320,
            function: (local_index) => {
              let local_pop = local_popc_raster.data[local_index];
              if (local_pop < 1.0) return 0;
              let pc_val = final_pc_data[local_index];
              if (!isFinite(pc_val) || pc_val <= 0) return 0;
              let total_val = Math.max(min_cell_floor, pc_val) * local_pop;
              return (isFinite(total_val) && total_val < 3.402823466e38) ? total_val : 0;
            }
          });
          
          //Sync to local 7.scaled_to_national if directory is present
          if (this.intermediate_gdp_local_scaled_to_national) {
            let local_scaled_dir = path.resolve(this.intermediate_gdp_local_scaled_to_national);
            if (fs.existsSync(local_scaled_dir)) {
              let local_copy_dest = path.join(local_scaled_dir, `${this.prefix}_${year}.png`);
              fs.copyFileSync(local_output_total, local_copy_dest);
            }
          }
        }
      });
    }
    
    /**
     * Step I: Verifies that final per capita and total GDP rasters exist.
     * @alias Eoscala_GDP.I_recalculateGDP_pcRasters
     * 
     * @param {Object} [arg0_options]
     *  @param {boolean} [arg0_options.overwrite=false]
     * @returns {Promise<void>}
     */
    static async I_recalculateGDP_pcRasters (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Declare local instance variables
      let hyde_years = (options.years) ? options.years : landuse_HYDE.sorted_hyde_years;
      let missing_years = [];
      
      for (let i = 0; i < hyde_years.length; i++) {
        let pc_file = `${this.output_gdp_pc_folder}${this.pc_prefix}_${hyde_years[i]}.png`;
        let total_file = `${this.intermediate_gdp_scaled_to_national}${this.prefix}_${hyde_years[i]}.png`;
        if (options.overwrite || !fs.existsSync(pc_file) || !fs.existsSync(total_file))
          missing_years.push(hyde_years[i]);
      }
      
      if (missing_years.length === 0) return;
      
      //Return statement: fallback if missing
      return this.H_scaleGDPRastersToNational(options);
    }
    
    /**
     * Unified pipeline execution orchestrator.
     * Follows the Maddison/MPD/Nordhaus/De Long sequence:
     * 1. Per capita is modelled, trained, and predicted across space.
     * 2. Per capita is normalised and blended with empirical SEDAC per capita.
     * 3. Per capita is calibrated to national targets (preserving intra-country variance).
     * 4. Per capita raster is saved FIRST.
     * 5. Total GDP raster aggregates strictly downstream: Total = PerCapita * Population.
     * @alias Eoscala_GDP.processRasters
     * 
     * @param {Object} [arg0_options]
     *  @param {Array<string>} [arg0_options.exclude]
     *  @param {boolean} [arg0_options.skip_training=false]
     * @returns {Promise<void>}
     */
    static async processRasters (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Initialise options
      if (!options.exclude) options.exclude = [];
      if (options.skip_training || options.use_existing_models || options.train === false) {
        if (!options.exclude.includes("B")) options.exclude.push("B");
        console.log(`[${this.pc_prefix}] Skipping Step B 2nd-pass OLS training (using existing models).`);
      }
      
      //1. Intensive calibration: Generate initial uniform per-capita target rasters
      if (!options.exclude.includes("A")) await this.A_generateGDP_pcRasters(options);
      
      //2. Spatial regression: Train OLS on per-capita GDP & predict continuous surfaces
      if (!options.exclude.includes("B")) await this.B_trainGDP_pcModels(options);
      if (!options.exclude.includes("C")) await this.C_generateOLS_GDP_pcRasters(options);
      if (!options.exclude.includes("D")) await this.D_normaliseGDP_pcRasters(options);
      
      //3. SEDAC historical blending in per-capita space
      if (!options.exclude.includes("E")) await this.E_generateGDPRasters(options);
      if (!options.exclude.includes("F")) await this.F_scaleGDPRastersToGlobal(options);
      if (!options.exclude.includes("G")) await this.G_interpolateToSEDAC(options);
      
      //4. Calibrate per-capita GDP to national targets FIRST, then aggregate Total GDP downstream
      if (!options.exclude.includes("H")) await this.H_scaleGDPRastersToNational(options);
      if (!options.exclude.includes("I")) await this.I_recalculateGDP_pcRasters(options);
    }
  };
}
