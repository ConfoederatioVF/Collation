//Initialise functions
{
  if (!global.Eoscala_GDP && typeof require !== "undefined") {
    let engine_path = (global.h3) ? path.resolve(h3, "Eoscala_GDP", "Eoscala_GDP.js") : path.resolve(__dirname, "../Eoscala_GDP/Eoscala_GDP.js");
    if (fs.existsSync(engine_path)) require(engine_path);
  }
  
  /**
   * Historical Purchasing Power Parity (PPP) GDP per capita pipeline.
   * Extends unified Eoscala_GDP.
   * 
   * @class GDP_PPP_pc
   * @augments Eoscala_GDP
   */
  global.GDP_PPP_pc = class extends Eoscala_GDP {
    static cf = `${h3}/GDP_PPP_pc/`;
    static mode = "PPP";
    static prefix = "GDP_PPP";
    static pc_prefix = "GDP_PPP_pc";
    
    static input_gdp_pc_folder = `${this.cf}rasters/`;
    static intermediate_ols_folder = `${this.cf}1.OLS/`;
    static intermediate_ols_rasters_folder = `${this.cf}2.OLS_PPP_pc_rasters/`;
    static intermediate_pc_estimates_folder = `${this.cf}3.PPP_pc_estimates/`;
    static intermediate_sedac_blended_folder = `${this.cf}4.sedac_blended/`;
    static intermediate_gdp_scaled_to_national = `${this.cf}5.scaled_to_national/`;
    static output_gdp_pc_folder = `${this.cf}6.GDP_PPP_pc_rasters/`;
    
    //Backward-compatible getters
    static get intermediate_gdp_interpolated () { return this.intermediate_sedac_blended_folder; }
    static get intermediate_gdp_ppp_interpolated () { return this.intermediate_sedac_blended_folder; }
    static get intermediate_gdp_local_scaled_to_national () { return this.intermediate_gdp_scaled_to_national; }
    static get intermediate_gdp_ppp_scaled_to_national () { return this.intermediate_gdp_scaled_to_national; }
    static get output_gdp_ppp_pc_folder () { return this.output_gdp_pc_folder; }
    
    //HYDE; Stadestér formatters
    static hf = () => `${landuse_HYDE.bf}/rasters/`;
    static hf1 = (y) => landuse_HYDE._getHYDEYearName(y);
    static sf = () => population_Velkscala;
    
    //Model calibration bindings
    static getGDPObject = () => GDP_PPP.getGDP_PPPObject();
    static getWorldGDPObject = () => GDP_PPP.getWorldGDP_PPPObject();
    static sedac_class = () => GDP_PPP_SEDAC;
    
    /**
     * Backward-compatible facade for single-year OLS training.
     * @alias GDP_PPP_pc.B_trainGDP_PPP_pcModel
     */
    static async B_trainGDP_PPP_pcModel (arg0_year, arg1_options) {
      //Return statement
      return this.B_trainGDP_pcModel(arg0_year, arg1_options);
    }
    
    /**
     * Backward-compatible facade for batch OLS training.
     * @alias GDP_PPP_pc.B_trainGDP_PPP_pcModels
     */
    static async B_trainGDP_PPP_pcModels (arg0_options) {
      //Return statement
      return this.B_trainGDP_pcModels(arg0_options);
    }
    
    /**
     * Backward-compatible facade for OLS raster generation.
     * @alias GDP_PPP_pc.C_generateOLS_GDP_PPP_pcRasters
     */
    static async C_generateOLS_GDP_PPP_pcRasters (arg0_options) {
      //Return statement
      return this.C_generateOLS_GDP_pcRasters(arg0_options);
    }
    
    /**
     * Backward-compatible facade for raster normalisation.
     * @alias GDP_PPP_pc.D_normaliseGDP_PPP_pcRasters
     */
    static async D_normaliseGDP_PPP_pcRasters (arg0_options) {
      //Return statement
      return this.D_normaliseGDP_pcRasters(arg0_options);
    }
    
    /**
     * Backward-compatible facade for total GDP raster generation.
     * @alias GDP_PPP_pc.E_generateGDP_PPPRasters
     */
    static async E_generateGDP_PPPRasters (arg0_options) {
      //Return statement
      return this.E_generateGDPRasters(arg0_options);
    }
    
    /**
     * Backward-compatible facade for national scaling.
     * @alias GDP_PPP_pc.H_scaleGDP_PPPRastersToNational
     */
    static async H_scaleGDP_PPPRastersToNational (arg0_options) {
      //Return statement
      return this.H_scaleGDPRastersToNational(arg0_options);
    }
    
    /**
     * Backward-compatible facade for per capita recalculation.
     * @alias GDP_PPP_pc.I_recalculateGDP_PPP_pcRasters
     */
    static async I_recalculateGDP_PPP_pcRasters (arg0_options) {
      //Return statement
      return this.I_recalculateGDP_pcRasters(arg0_options);
    }
  };
}