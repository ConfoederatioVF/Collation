//Initialise functions
{
  if (!global.Eoscala_GDP && typeof require !== "undefined") {
    let engine_path = (global.h3) ? path.resolve(h3, "Eoscala_GDP", "Eoscala_GDP.js") : path.resolve(__dirname, "../Eoscala_GDP/Eoscala_GDP.js");
    if (fs.existsSync(engine_path)) require(engine_path);
  }
  
  /**
   * Historical Nominal GDP and GDP per capita pipeline.
   * Extends unified Eoscala_GDP.
   * 
   * @class GDP_pc
   * @augments Eoscala_GDP
   */
  global.GDP_pc = class extends Eoscala_GDP {
    static cf = `${h3}/GDP_pc/`;
    static mode = "nominal";
    static prefix = "GDP";
    static pc_prefix = "GDP_pc";
    
    static input_gdp_pc_folder = `${this.cf}rasters/`;
    static intermediate_ols_folder = `${this.cf}1.OLS/`;
    static intermediate_ols_rasters_folder = `${this.cf}2.OLS_pc_estimates/`;
    static intermediate_pc_estimates_folder = `${this.cf}3.pc_estimates/`;
    static intermediate_sedac_blended_folder = `${this.cf}4.sedac_blended/`;
    static intermediate_gdp_scaled_to_national = `${this.cf}5.scaled_to_national/`;
    static output_gdp_pc_folder = `${this.cf}6.GDP_nominal_pc_rasters/`;
    
    //Backward-compatible getters
    static get intermediate_gdp_interpolated () { return this.intermediate_sedac_blended_folder; }
    static get intermediate_gdp_local_scaled_to_national () { return this.intermediate_gdp_scaled_to_national; }
    
    //HYDE; Stadestér formatters
    static hf = () => `${landuse_HYDE.bf}/rasters/`;
    static hf1 = (y) => landuse_HYDE._getHYDEYearName(y);
    static sf = () => population_Stadester;
    
    //Model calibration bindings
    static getGDPObject = () => GDP_nominal.getGDPObject();
    static getWorldGDPObject = () => GDP_nominal.getWorldGDPObject();
    static sedac_class = () => GDP_nominal_SEDAC;
    
    /**
     * Backward-compatible facade for single-year OLS training.
     * @alias GDP_pc.B_trainGDP_pcModel
     */
    static async B_trainGDP_pcModel (arg0_year, arg1_options) {
      //Return statement
      return super.B_trainGDP_pcModel(arg0_year, arg1_options);
    }
    
    /**
     * Backward-compatible facade for batch OLS training.
     * @alias GDP_pc.B_trainGDP_pcModels
     */
    static async B_trainGDP_pcModels (arg0_options) {
      //Return statement
      return super.B_trainGDP_pcModels(arg0_options);
    }
    
    /**
     * Backward-compatible facade for OLS raster generation.
     * @alias GDP_pc.C_generateOLS_GDP_pcRasters
     */
    static async C_generateOLS_GDP_pcRasters (arg0_options) {
      //Return statement
      return super.C_generateOLS_GDP_pcRasters(arg0_options);
    }
    
    /**
     * Backward-compatible facade for raster normalisation.
     * @alias GDP_pc.D_normaliseGDP_pcRasters
     */
    static async D_normaliseGDP_pcRasters (arg0_options) {
      //Return statement
      return super.D_normaliseGDP_pcRasters(arg0_options);
    }
    
    /**
     * Backward-compatible facade for total GDP raster generation.
     * @alias GDP_pc.E_generateGDPRasters
     */
    static async E_generateGDPRasters (arg0_options) {
      //Return statement
      return super.E_generateGDPRasters(arg0_options);
    }
    
    /**
     * Backward-compatible facade for national scaling.
     * @alias GDP_pc.H_scaleGDPRastersToNational
     */
    static async H_scaleGDPRastersToNational (arg0_options) {
      //Return statement
      return super.H_scaleGDPRastersToNational(arg0_options);
    }
    
    /**
     * Backward-compatible facade for per capita recalculation.
     * @alias GDP_pc.I_recalculateGDP_pcRasters
     */
    static async I_recalculateGDP_pcRasters (arg0_options) {
      //Return statement
      return super.I_recalculateGDP_pcRasters(arg0_options);
    }
  };
}