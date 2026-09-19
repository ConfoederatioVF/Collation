global.wealth_income_OLS = class {
	static bf = `${h2}/wealth_income_OLS/`;
	
	//Folders
	static intermediate_ols_models_folder = `${this.bf}1.OLS_models/`;
	static intermediate_ols_rasters_folder = `${this.bf}2.OLS_rasters/`;
	
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
		"gdp_nominal": (y) => [`${GDP_pc.intermediate_gdp_scaled_to_national}/GDP_${y}.png`, "float32"],
		"gdp_pc": (y) => [`${GDP_pc.output_gdp_pc_folder}/GDP_pc_${y}.png`, "float32"],
		"gdp_ppp": (y) => [`${GDP_PPP_pc.intermediate_gdp_ppp_scaled_to_national}/GDP_PPP_${y}.png`, "float32"],
		"gdp_ppp_pc": (y) => [`${GDP_PPP_pc.output_gdp_ppp_pc_folder}/GDP_PPP_pc_${y}.png`, "float32"],
		"gini": (y) => [`${gini_Eoscala.output_rasters}gini_${y}.png`, "float32"],
		
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
	
	static async A_trainWIDModels (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		if (!options.lambda) options.lambda = 1e6;
		if (!options.weighting_function) options.weighting_function = (value) => Math.abs(value);
		
		//Declare local instance variables
		let variables = wealth_income_WID.options.variables;
		let years = landuse_HYDE.sorted_hyde_years;
		
		for (let i = 0; i < variables.length; i++) {
			let current_variable = variables[i];
			let local_models_folder = `${this.intermediate_ols_models_folder}${current_variable}/`;
			
			if (!fs.existsSync(local_models_folder)) fs.mkdirSync(local_models_folder, { recursive: true });
			
			console.log(`Processing OLS Training for ${current_variable}.`);
			
			//Iterate over all HYDE years
			for (let x = 0; x < years.length; x++) {
				let current_year = years[x];
				let utility_raster_path = `${wealth_income_WID.bf}${current_variable}/${current_variable}_${current_year}.png`;
				
				if (fs.existsSync(utility_raster_path)) {
					console.log(`- Loading covariates for ${current_variable} (${current_year})`);
					
					let covariates_obj = await Statistics.loadOLSCovariates(utility_raster_path, {
						utility_format: "float32",
						covariates_obj: this.covariates_obj,
						formatting_parameters: [current_year]
					});
					
					//Crucial step: Filter out Zero Values (Missing WID Data) to prevent them skewing OLS regression
					let filtered_X = [];
					let filtered_Y = [];
					
					for (let j = 0; j < covariates_obj.Y.length; j++) {
						let utility_val = covariates_obj.Y[j][0];
						if (utility_val !== 0 && !isNaN(utility_val)) {
							filtered_X.push(covariates_obj.X[j]);
							filtered_Y.push(covariates_obj.Y[j]);
						}
					}
					
					//Override matrices with cleanly filtered ones
					covariates_obj.X = filtered_X;
					covariates_obj.Y = filtered_Y;
					
					//Check if we still have valid data points remaining
					if (covariates_obj.X.length === 0) {
						console.warn(`- No valid non-zero data points for ${current_variable} in ${current_year}. Skipping OLS.`);
						continue;
					}
					
					//Train and write model to JSON
					let output_file_path = `${local_models_folder}OLS_${current_variable}_${current_year}.json`;
					
					await Statistics.trainOLSModel(output_file_path, covariates_obj, {
						...options,
						key: `${current_variable}_${current_year}`
					});
					await Blacktraffic.yield();
				}
			}
		}
	}
	
	static async B_geomeanWIDModels (arg0_options) {
		let options = (arg0_options) ? arg0_options : {};
		let variables = wealth_income_WID.options.variables;
		
		for (let i = 0; i < variables.length; i++) {
			let current_variable = variables[i];
			let local_models_folder = `${this.intermediate_ols_models_folder}${current_variable}/`;
			
			if (fs.existsSync(local_models_folder)) {
				console.log(`\n--- Aggregating Temporal Models (Geometric Mean) for ${current_variable} ---`);
				
				//Using the trailing underscore prefix isolates the correct target jsons and results in a clean format_slug: geomean_OLS_${current_variable}.json
				await Statistics.geomeanOLSModels(local_models_folder, `OLS_${current_variable}_`, options);
			}
		}
	}
	
	static async C_generateOLSRasters () {
		//Declare local instance variables
		let variables = wealth_income_WID.options.variables;
		let years = landuse_HYDE.sorted_hyde_years;
		let landarea_raster = GeoPNG.loadNumberRasterImage(metadata_HYDE.input_raster_land_area, {
			format: "int32"
		});
		
		for (let i = 0; i < variables.length; i++) {
			let current_variable = variables[i];
			let local_models_folder = `${this.intermediate_ols_models_folder}${current_variable}/`;
			let local_rasters_folder = `${this.intermediate_ols_rasters_folder}${current_variable}/`;
			
			if (!fs.existsSync(local_rasters_folder)) fs.mkdirSync(local_rasters_folder, { recursive: true });
			
			console.log(`Generating OLS Rasters for ${current_variable}.`);
			
			//Load the unified geomean model for the variable
			let geomean_model_path = `${local_models_folder}geomean_OLS_${current_variable}.json`;
			if (!fs.existsSync(geomean_model_path)) {
				console.warn(`- Missing Geomean model for ${current_variable} at ${geomean_model_path}. Skipping raster generation.`);
				continue;
			}
			let model_obj = JSON.parse(fs.readFileSync(geomean_model_path, "utf8"));
			
			//Iterate over all HYDE years applying the unified structural coefficients
			for (let x = 0; x < years.length; x++) {
				let current_year = years[x];
				let local_output_path = `${local_rasters_folder}OLS_${current_variable}_${current_year}.png`;
				
				await Statistics.generateOLSRaster(local_output_path, {
					covariates_obj: this.covariates_obj,
					format: "float32",
					formatting_parameters: [current_year],
					model_obj: model_obj, // Pass the static, averaged JSON
					
					guard_clause: (local_index, rasters_obj) => {
						//Skip calculating values over unpopulated areas and ocean pixels
						let local_population = Math.returnSafeNumber(rasters_obj["popd_"]?.data[local_index], 0);
						return !(local_population === 0 || landarea_raster.data[local_index] === 0);
					}
				});
				await Blacktraffic.yield();
			}
		}
	}
	
	static async processRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		if (!options.exclude) options.exclude = [];
		if (options.skip_training || options.use_existing_models || options.train === false) {
			if (!options.exclude.includes("A")) options.exclude.push("A");
			if (!options.exclude.includes("B")) options.exclude.push("B");
			console.log(`[wealth_income_OLS] Skipping Steps A & B training (using existing models).`);
		}
		
		//1. Train annual OLS Variable Models
		if (!options.exclude.includes("A")) await this.A_trainWIDModels(options);
		
		//2. Compress annual models into a single, temporal model per variable
		if (!options.exclude.includes("B")) await this.B_geomeanWIDModels(options);
		
		//3. Raster Generation Phase (Backcalculating all years using unified model)
		if (!options.exclude.includes("C")) await this.C_generateOLSRasters();
	}
};