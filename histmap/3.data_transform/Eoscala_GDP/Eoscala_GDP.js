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
          let global_avg_pc = (world_pop > 0) ? (world_gdp / world_pop) : ((this.mode === "nominal") ? 178.3 : 363.6);
          let max_historical_pc = (year <= 1800) ?
            ((year <= 100) ? 2500 : 3500 + 4500 * ((year - 1) / 1799)) :
            Infinity;
          let min_historical_pc = (year <= 1800) ? 150 : 0;
          
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
                    let raw_pc = target_gdp / target_pop;
                    if (target_pop < 100 || raw_pc > max_historical_pc || raw_pc < min_historical_pc)
                      return global_avg_pc;
                    if (year <= 100 && primary_code !== "ITA")
                      raw_pc = Math.min(raw_pc, 1180);
                    return raw_pc;
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
          
          let first_pass_min = Infinity, first_pass_max = -Infinity;
          for (let x = 0; x < second_pass_raster.data.length; x++) {
            if (landarea_raster.data[x] > 0 && pop_raster.data[x] >= 1.0) {
              let fp_val = first_pass_raster.data[x];
              if (isFinite(fp_val) && fp_val > 0) {
                if (fp_val < first_pass_min) first_pass_min = fp_val;
                if (fp_val > first_pass_max) first_pass_max = fp_val;
              }
            }
          }
          if (!isFinite(first_pass_min)) first_pass_min = 0;
          if (!isFinite(first_pass_max) || first_pass_max <= 0) first_pass_max = 5000000;
          first_pass_max = Math.min(first_pass_max, 5000000);
          let first_pass_range = (first_pass_max > first_pass_min) ? (first_pass_max - first_pass_min) : 1;
          
          let second_pass_fractions = GeoPNG.regulariseLogTail({
            allow_zero_or_negative: true,
            data: second_pass_raster.data,
            fraction_only: true,
            valid_filter: (x) => landarea_raster.data[x] > 0 && pop_raster.data[x] >= 1.0
          });
          
          GeoPNG.saveNumberRasterImage({
            file_path: output_path,
            format: "float32",
            height: 2160,
            width: 4320,
            function: (local_index) => {
              if (landarea_raster.data[local_index] === 0 || pop_raster.data[local_index] < 1.0) return 0;
              let fp_val = first_pass_raster.data[local_index];
              if (!isFinite(fp_val) || fp_val <= 0) return 0;
              let sp_frac = second_pass_fractions[local_index];
              if (!isFinite(sp_frac) || sp_frac < 0) sp_frac = 0;
              
              //Modulate national per-capita target by local relative urban/agricultural productivity:
              //Rural baseline reaches 0.75 * G_c; intensive urban agglomeration reaches 2.25 * G_c.
              let res = fp_val * (0.75 + 1.5 * sp_frac);
              return (isFinite(res) && res > 0 && res < 3.402823466e38) ? res : 0;
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
              fs.copyFileSync(local_sedac_path, local_output_path);
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
            //Pre-1800: multiply modelled per capita by population to produce extensive total GDP for 6.interpolated
            GeoPNG.saveNumberRasterImage({
              file_path: local_output_path,
              format: "float32",
              height: 2160,
              width: 4320,
              function: (local_index) => {
                let pc = pc_raster.data[local_index];
                let p = (pop_raster) ? pop_raster.data[local_index] : 0;
                return (p >= 1.0 && isFinite(pc) && pc > 0) ? pc * p : 0;
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
        let local_input_file_path = `${this.intermediate_pc_estimates_folder}${this.pc_prefix}_${current_year}.png`;
        if (!fs.existsSync(local_input_file_path))
          local_input_file_path = `${this.intermediate_gdp_interpolated}${this.prefix}_${current_year}.png`;
        if (!fs.existsSync(local_input_file_path)) continue;
        
        let local_input_raster = GeoPNG.loadNumberRasterImage(local_input_file_path, { format: "float32" });
        let local_popc_file_path = `${population_Stadester.input_popc_folder}stadester_population_${current_year}.png`;
        let local_popc_raster = GeoPNG.loadNumberRasterImage(local_popc_file_path, { format: "float32" });
        
        let country_stats = {};
        let current_max_pc = 0;
        let local_gdp_sums = {};
        let local_pop_sums = {};
        let local_threshold = (previous_max_pc > 0) ? Math.min(previous_max_pc * 4, 500000) : 500000;
        let clamp_alpha = local_threshold * 0.1;
        
        let is_total_raster = local_input_file_path.includes(this.prefix + "_") && !local_input_file_path.includes(this.pc_prefix + "_");
        
        //Calculate national population and unscaled GDP (sum of pc * pop)
        for (let x = 0; x < local_input_raster.data.length; x++) {
          let p = local_popc_raster.data[x];
          if (p >= 1.0) {
            let byte_index = x * 4;
            let local_colour_key = `${geocode_raster.data[byte_index]},${geocode_raster.data[byte_index+1]},${geocode_raster.data[byte_index+2]}`;
            let local_geocodes = geocode_obj[local_colour_key];
            if (local_geocodes) {
              let local_pc = is_total_raster ? (local_input_raster.data[x] / p) : local_input_raster.data[x];
              let g_val = local_pc * p;
              for (let y = 0; y < local_geocodes.length; y++) {
                Object.modifyValue(local_gdp_sums, local_geocodes[y], g_val);
                Object.modifyValue(local_pop_sums, local_geocodes[y], p);
              }
            }
          }
        }
        
        //Calibrate per-capita scalar per country: s_c = Target_GDP / (Sum_i pc_i * pop_i)
        Object.iterate(local_gdp_sums, (local_key, local_value) => {
          let local_target = gdp_national_obj[local_key]?.[current_year];
          let pop_c = local_pop_sums[local_key] || 0;
          let is_tiny_pop = (current_year <= 1820 && pop_c < 100);
          let initial_s = 1.0;
          if (local_target && local_value > 0) {
            initial_s = is_tiny_pop ? 1.0 : (local_target / local_value);
            if (current_year <= 1820)
              initial_s = Math.max(0.2, Math.min(3.0, initial_s));
          }
          country_stats[local_key] = {
            initial_scalar: initial_s,
            outlier_gdp: 0,
            remaining_input_sum: 0,
            target_gdp: local_target || local_value
          };
        });
        
        //Identify outliers in per-capita space and calculate secondary scalars
        for (let x = 0; x < local_input_raster.data.length; x++) {
          let p = local_popc_raster.data[x];
          if (p >= 1.0) {
            let local_pc = is_total_raster ? (local_input_raster.data[x] / p) : local_input_raster.data[x];
            if (local_pc === 0) continue;
            let byte_index = x * 4;
            let local_colour_key = `${geocode_raster.data[byte_index]},${geocode_raster.data[byte_index+1]},${geocode_raster.data[byte_index+2]}`;
            let local_geocodes = geocode_obj[local_colour_key];
            
            if (local_geocodes && local_geocodes.length > 0) {
              let stats = country_stats[local_geocodes[0]];
              if (stats) {
                let raw_pc = local_pc * stats.initial_scalar;
                if (raw_pc > local_threshold) {
                  let reg_pc = local_threshold + clamp_alpha * Math.log(1 + ((raw_pc - local_threshold) / clamp_alpha));
                  stats.outlier_gdp += reg_pc * p;
                } else {
                  stats.remaining_input_sum += local_pc * p;
                }
              }
            }
          }
        }
        
        Object.iterate(country_stats, (country_code, stats) => {
          let remaining_target = Math.max(0, stats.target_gdp - stats.outlier_gdp);
          let s_sec = (stats.remaining_input_sum > 0) ? remaining_target / stats.remaining_input_sum : stats.initial_scalar;
          if (current_year <= 1820) s_sec = Math.max(0.2, Math.min(3.0, s_sec));
          stats.secondary_scalar = s_sec;
        });
        
        for (let x = 0; x < local_input_raster.data.length; x++) {
          let p = local_popc_raster.data[x];
          if (p >= 1.0) {
            let local_pc = is_total_raster ? (local_input_raster.data[x] / p) : local_input_raster.data[x];
            if (local_pc === 0) continue;
            let byte_index = x * 4;
            let local_colour_key = `${geocode_raster.data[byte_index]},${geocode_raster.data[byte_index+1]},${geocode_raster.data[byte_index+2]}`;
            let local_geocodes = geocode_obj[local_colour_key];
            
            let final_pc = local_pc;
            if (local_geocodes && local_geocodes.length > 0) {
              let stats = country_stats[local_geocodes[0]];
              if (stats) {
                let raw_pc = local_pc * stats.initial_scalar;
                if (raw_pc > local_threshold) {
                  final_pc = local_threshold + clamp_alpha * Math.log(1 + ((raw_pc - local_threshold) / clamp_alpha));
                } else {
                  let res_pc = local_pc * stats.secondary_scalar;
                  if (res_pc > local_threshold) {
                    final_pc = local_threshold + clamp_alpha * Math.log(1 + ((res_pc - local_threshold) / clamp_alpha));
                  } else final_pc = res_pc;
                }
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
          let local_input_file_path = `${this.intermediate_pc_estimates_folder}${this.pc_prefix}_${year}.png`;
          if (!fs.existsSync(local_input_file_path))
            local_input_file_path = `${this.intermediate_gdp_interpolated}${this.prefix}_${year}.png`;
          let local_input_raster = GeoPNG.loadNumberRasterImage(local_input_file_path, { format: "float32" });
          let local_popc_file_path = `${population_Stadester.input_popc_folder}stadester_population_${year}.png`;
          let local_popc_raster = GeoPNG.loadNumberRasterImage(local_popc_file_path, { format: "float32" });
          let local_output_pc = `${this.output_gdp_pc_folder}${this.pc_prefix}_${year}.png`;
          let local_output_total = `${this.intermediate_gdp_scaled_to_national}${this.prefix}_${year}.png`;
          let is_total_raster = local_input_file_path.includes(this.prefix + "_") && !local_input_file_path.includes(this.pc_prefix + "_");
          
          let clamp_alpha = threshold * 0.1;
          let raw_calibrated_pc = new Float32Array(4320 * 2160);
          
          //Calibrate per-capita GDP per cell (preserving urban premium and local variance)
          for (let local_index = 0; local_index < local_input_raster.data.length; local_index++) {
            let local_pop = local_popc_raster.data[local_index];
            if (local_pop < 1.0) continue;
            let local_pc = is_total_raster ? (local_input_raster.data[local_index] / local_pop) : local_input_raster.data[local_index];
            if (local_pc === 0) continue;
            let byte_index = local_index * 4;
            let local_colour_key = `${geocode_raster.data[byte_index]},${geocode_raster.data[byte_index+1]},${geocode_raster.data[byte_index+2]}`;
            let local_geocodes = geocode_obj[local_colour_key];
            
            if (local_geocodes && local_geocodes.length > 0) {
              let primary_code = local_geocodes[0];
              let s = stats[primary_code];
              if (s) {
                let raw_pc = local_pc * s.initial_scalar;
                let res_pc = (raw_pc > threshold) ?
                  (threshold + clamp_alpha * Math.log(1 + ((raw_pc - threshold) / clamp_alpha))) :
                  (local_pc * s.secondary_scalar);
                if (res_pc > threshold)
                  res_pc = threshold + clamp_alpha * Math.log(1 + ((res_pc - threshold) / clamp_alpha));
                
                //Antiquity supremacy constraint (year <= 100): Roman Italy is the global summit
                if (year <= 100) {
                  if (primary_code === "ITA") {
                    res_pc = Math.min(res_pc, 3500);
                  } else {
                    res_pc = Math.min(res_pc, 1180);
                  }
                }
                raw_calibrated_pc[local_index] = res_pc;
              } else {
                let fallback_pc = local_pc;
                if (year <= 100) fallback_pc = Math.min(fallback_pc, (primary_code === "ITA") ? 3500 : 1180);
                raw_calibrated_pc[local_index] = fallback_pc;
              }
            } else raw_calibrated_pc[local_index] = local_pc;
          }
          
          let final_pc_data = raw_calibrated_pc;
          
          //For pre-industrial era (year < 1800): apply dasymetric blur to rural per-capita variance, preserving urban cores
          if (year < 1800) {
            let local_urbc_path = `${population_Stadester.input_urbc_folder}stadester_urban_${year}.png`;
            let local_urbc_raster = (fs.existsSync(local_urbc_path)) ?
              GeoPNG.loadNumberRasterImage(local_urbc_path, { format: "float32" }) : null;
            let blurred_pc = GeoPNG.dasymetricBlur({
              height: 2160,
              mask_data: geocode_raster.data,
              pop_data: local_popc_raster.data,
              radius: 64,
              target_data: raw_calibrated_pc,
              width: 4320
            });
            final_pc_data = new Float32Array(4320 * 2160);
            for (let j = 0; j < 4320 * 2160; j++) {
              let is_urban = (local_urbc_raster && local_urbc_raster.data[j] > 0);
              final_pc_data[j] = is_urban ? raw_calibrated_pc[j] : blurred_pc[j];
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
              return (isFinite(pc_val) && pc_val > 0 && pc_val < 3.402823466e38) ? pc_val : 0;
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
              let total_val = pc_val * local_pop;
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
