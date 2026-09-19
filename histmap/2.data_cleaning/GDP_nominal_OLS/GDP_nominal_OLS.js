global.GDP_nominal_OLS = class {
	static bf = `${h2}/GDP_nominal_OLS/`;
	static input_coefficients_json = () => `${GDP_nominal_SEDAC.intermediate_ols_folder}geomean_OLS_GDP.json`;
	static input_covariates_obj = () => GDP_PPP_SEDAC.covariates_obj;
	static output_ols_folder = `${this.bf}rasters/`;
	
	//HYDE; Stadestér formatters
	static hf = () => `${landuse_HYDE.bf}/rasters/`;
	static hf1 = (y) => landuse_HYDE._getHYDEYearName(y);
	static sf = () => population_Stadester;
	
	static async A_generateOLS_GDPRaster (arg0_year) {
		//Convert from parameters
		let year = arg0_year;
		
		//Declare local instance variables
		let landarea_raster = GeoPNG.loadNumberRasterImage(metadata_HYDE.input_raster_land_area, {
			format: "int32"
		});
		let output_file_path = `${this.output_ols_folder}OLS_GDP_${year}.png`;
		
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
	
	static async A_generateOLS_GDPRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Declare local instance variables
		let all_cov_keys = Object.keys(this.input_covariates_obj());
		let cov_func_map = this.input_covariates_obj();
		let hyde_years = landuse_HYDE.sorted_hyde_years;
		let model_path = this.input_coefficients_json();
		
		if (!fs.existsSync(this.output_ols_folder)) fs.mkdirSync(this.output_ols_folder, { recursive: true });
		
		//Return statement
		return await Statistics.generateOLSRastersParallel(hyde_years, (year) => {
			let covariates_map = {};
			for (let i = 0; i < all_cov_keys.length; i++) {
				let local_key = all_cov_keys[i];
				let local_val = cov_func_map[local_key](year);
				covariates_map[local_key] = local_val;
			}
			
			return {
				covariates_map: covariates_map,
				model_obj: model_path,
				options: {
					format: "float32"
				},
				output_file_path: `${this.output_ols_folder}OLS_GDP_${year}.png`
			};
		}, {
			concurrency: options.concurrency,
			name: "GDP Nominal OLS Raster Generation"
		});
	}
	
	static async processRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		if (!options.exclude) options.exclude = [];
		
		//1. Generate OLS rasters
		if (!options.exclude.includes("A")) await this.A_generateOLS_GDPRasters(options);
	}
};