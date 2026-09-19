//Initialise functions
{
  if (!global.population_Stadester_Legacy) {
    if (global.population_Stadester) {
      global.population_Stadester_Legacy = global.population_Stadester;
    } else {
      global.population_Stadester_Legacy = class extends (global.population_Stadester || Object) {
        static get bf () { return global.population_Stadester ? global.population_Stadester.bf : `${h2}/population_Stadester/`; }
        static get input_popc_folder () { return global.population_Stadester ? global.population_Stadester.input_popc_folder : `${this.bf}stadester_population_rasters/`; }
        static get input_rurc_folder () { return global.population_Stadester ? global.population_Stadester.input_rurc_folder : `${this.bf}stadester_rural_rasters/`; }
        static get input_urbc_folder () { return global.population_Stadester ? global.population_Stadester.input_urbc_folder : `${this.bf}stadester_urban_rasters/`; }
        static get intermediate_base_folder () { return global.population_Stadester ? global.population_Stadester.intermediate_base_folder : `${this.bf}stadester_base_rasters/`; }
        static get intermediate_ghsl_folder () { return global.population_Stadester ? global.population_Stadester.intermediate_ghsl_folder : `${this.bf}stadester_ghsl_rasters/`; }
        static get intermediate_popd_folder () { return global.population_Stadester ? global.population_Stadester.intermediate_popd_folder : `${this.bf}stadester_density_rasters/`; }
        
        static async A_prepareIntermediates (arg0_options) {
          if (global.population_Stadester && global.population_Stadester.J_prepareIntermediates)
            return global.population_Stadester.J_prepareIntermediates(arg0_options);
        }
        
        static async processRasters (arg0_options) {
          if (global.population_Stadester && global.population_Stadester.processRasters)
            return global.population_Stadester.processRasters(arg0_options);
        }
      };
    }
  }
}