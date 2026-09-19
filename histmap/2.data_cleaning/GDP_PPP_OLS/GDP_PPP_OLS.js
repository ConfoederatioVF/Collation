global.GDP_PPP_OLS = class {
	static bf = `${h2}/GDP_PPP_OLS/`;
	static input_coefficients_json = () => `${GDP_PPP_SEDAC.intermediate_ols_folder}geomean_OLS_GDP_PPP.json`;
	static input_covariates_obj = () => GDP_PPP_SEDAC.covariates_obj;
	static output_ols_folder = `${this.bf}rasters/`;
	
	//HYDE; Stadestér formatters
	static hf = () => `${landuse_HYDE.bf}/rasters/`;
	static hf1 = (y) => landuse_HYDE._getHYDEYearName(y);
	static sf = () => population_Stadester;
	
	static async A_generateOLS_GDP_PPPRaster (arg0_year) {
		//Convert from parameters
		let year = arg0_year;
		
		//Declare local instance variables
		let landarea_raster = GeoPNG.loadNumberRasterImage(metadata_HYDE.input_raster_land_area, {
			format: "int32"
		});
		let output_file_path = `${this.output_ols_folder}OLS_GDP_PPP_${year}.png`;
		
		//Return statement
		return Statistics.generateOLSRaster(output_file_path, {
			covariates_obj: this.input_covariates_obj(),
			format: "float32",
			formatting_parameters: [year],
			model_obj: this.input_coefficients_json(),
			
			guard_clause: (local_index, rasters_obj) => {
				//Declare local instance variables
				let local_population = Math.returnSafeNumber(rasters_obj["popd_"]?.data[local_index], 0);
				
				//Return statement; guard clause for uninhabited pixels and HYDE clamping
				return !(local_population === 0 || landarea_raster.data[local_index] === 0);
			}
		});
	}
	
	static async A_generateOLS_GDP_PPPRasters () {
		//Declare local instance variables
		let hyde_years = landuse_HYDE.sorted_hyde_years;
		
		//Iterate over all hyde_years and call A_generateOLS_GDP_PPPRaster
		for (let i = 0; i < hyde_years.length; i++) {
			await this.A_generateOLS_GDP_PPPRaster(hyde_years[i]);
			await Blacktraffic.yield();
		}
	}
	
	static async processRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		if (!options.exclude) options.exclude = [];
		
		//1. Generate OLS rasters
		if (!options.exclude.includes("A")) await this.A_generateOLS_GDP_PPPRasters();
	}
};