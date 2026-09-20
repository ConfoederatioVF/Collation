global.GDP_PPP_SEDAC = class {
	static bf = `${h1}/GDP_PPP_SEDAC/`;
	static intermediate_folder = `${h2}/GDP_PPP_SEDAC/`;
	static intermediate_ols_folder = `${h2}/GDP_PPP_SEDAC/OLS/`;
	static years = Array.getFilledDomain(1990, 2022);
	
	//Hyde; Stadestér formatters
	static hf = () => `${landuse_HYDE.bf}/rasters/`;
	static hf1 = (y) => landuse_HYDE._getHYDEYearName(y);
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
		"tot_irri": (y) => [`${this.hf()}/tot_irri${this.hf1(y)}_number.png`, "float32"],
		"tot_rainfed": (y) => [`${this.hf()}/tot_rainfed${this.hf1(y)}_number.png`, "float32"],
		"tot_rice": (y) => [`${this.hf()}/tot_rice${this.hf1(y)}_number.png`, "float32"],
		"uopp_": (y) => [`${this.hf()}/uopp_${this.hf1(y)}_number.png`, "float32"],
		
		//POP (Demographics)
		//We only include popd_, rurc_, urbc_ to prevent double-counting pops
		"popd_": (y) => [`${this.sf().intermediate_popd_folder}/stadester_density_${y}.png`, "float32"],
		"rurc_": (y) => [`${this.sf().input_rurc_folder}/stadester_rural_${y}.png`, "float32"],
		"urbc_": (y) => [`${this.sf().input_urbc_folder}/stadester_urban_${y}.png`, "float32"]
	};
	
	/**
	 * Returns a PNG array after converting GDP (PPP) 2017$100s from .geotiff to .png.
	 *
	 * @returns {Array<Object>}
	 */
	static async A_convertToPNGs () {
		//Return statement
		return GeoTIFF.convertToPNGs(`${GDP_PPP_SEDAC.bf}/GDP_PPP_1990_2022.tif`, `${GDP_PPP_SEDAC.bf}/GDP_PPP`, {
			format: "float32",
			years: GDP_PPP_SEDAC.years
		});
	}
	
	static async B_loadCovariates (arg0_year) {
		//Convert from parameters
		let year = arg0_year;
		
		//Declare local instance variables
		let input_file_path = `${this.bf}/GDP_PPP_${year}.png`;
		
		//Return statement
		return Statistics.loadOLSCovariates(input_file_path, {
			utility_format: "float32",
			
			covariates_obj: this.covariates_obj,
			formatting_parameters: [year]
		});
	}
	
	static async B_trainGDP_PPPModel (arg0_year, arg1_options) {
		//Convert from parameters
		let year = parseInt(arg0_year);
		let options = (arg1_options) ? arg1_options : {};
		
		//Initialise options
		if (!options.lambda) options.lambda = 1e11; //x100 from Eoscala 1.3, since it is no longer $100s.
		if (!options.key) options.key = year.toString();
		
		//Declare local instance variables
		let covariates_obj = await this.B_loadCovariates(year);
		let output_file_path =  `${this.intermediate_ols_folder}/OLS_GDP_PPP_${year}.json`;
		
		//Return statement
		return Statistics.trainOLSModel(output_file_path, covariates_obj, options);
	}
	
	static async B_trainGDP_PPPModels (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Declare local instance variables
		let all_covariate_keys = Object.keys(this.covariates_obj);
		let lambda_val = (options.lambda !== undefined) ? options.lambda : 1e11;
		
		//Return statement
		return await Statistics.trainOLSModelsParallel(this.years, (year) => {
			let covariates_map = {};
			for (let i = 0; i < all_covariate_keys.length; i++) {
				let local_key = all_covariate_keys[i];
				let local_val = this.covariates_obj[local_key](year);
				covariates_map[local_key] = local_val;
			}
			
			return {
				covariates_map: covariates_map,
				options: {
					...options,
					key: year.toString(),
					lambda: lambda_val
				},
				output_file_path: `${this.intermediate_ols_folder}/OLS_GDP_PPP_${year}.json`,
				target_file_path: `${this.bf}/GDP_PPP_${year}.png`,
				target_format: "float32"
			};
		}, {
			concurrency: options.concurrency,
			name: "GDP PPP SEDAC OLS Training"
		});
	}
	
	static async C_geomeanGDP_PPPModel (arg0_prefix) {
		//Convert from parameters
		let prefix = (arg0_prefix) ? arg0_prefix : "OLS_GDP_PPP_";
		
		//Return statement
		return Statistics.geomeanOLSModels(this.intermediate_ols_folder, prefix, {
			weighting_function: (value) => Math.abs(value) //Flip positive to adjust for collinearity
		});
	}
	
	static async D_processGDP_PPPModel (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Declare local instance variables
		let model_file_path = `${this.intermediate_ols_folder}/geomean_OLS_GDP_PPP.json`;
		let output_file_path = `${this.intermediate_ols_folder}/processed_base_model.json`;
		
		//Return statement
		return Statistics.processOLSModel(model_file_path, {
			...options,
			output_file_path,
			
			covariates_obj: this.covariates_obj,
			target: (y) => [`${this.bf}/GDP_PPP_${y}.png`, "float32"],
			steps: this.years,
		});
	}
	
	static async processRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		if (!options.exclude) options.exclude = [];
		let skip_training = (options.skip_training || options.use_existing_models || options.train === false);
		
		//1. Convert to PNGs
		if (!options.exclude.includes("A")) {
			await this.A_convertToPNGs();
			await population_Stadester.processRasters();
		}
		
		//2. Train individual yearly OLS models
		if (!options.exclude.includes("B") && !skip_training) await this.B_trainGDP_PPPModels(options);
		
		//3. Compute geomean
		if (!options.exclude.includes("C") && !skip_training) try {
			await this.C_geomeanGDP_PPPModel("OLS_GDP_PPP_");
		} catch (e) { console.error(e); }
		
		//4. Bidirectionally adjust weights
		//if (!options.exclude.includes("D")) await this.D_processGDP_PPPModel(options);
	}
};