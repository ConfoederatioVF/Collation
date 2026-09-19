global.gini_OLS = class {
	static bf = `${h2}/gini_OLS/`;
	static input_gini_premodern_csv = `${h1}/gini_Eoscala/gini_-21500_1800.csv`;
	static input_gini_modern_csv = `${h1}/gini_Eoscala/gini_1800_2018.csv`;
	static input_gini_subngini_json = () => gini_SubNGini.output_areal_json;
	static intermediate_ols_eoscala = `${this.bf}OLS_Eoscala/`;
	static intermediate_ols_gapminder = `${this.bf}OLS_Gapminder/`;
	static intermediate_ols_subngini = `${this.bf}OLS_SubNGini/`;
	
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
	
	static options = {
		eoscala_domain: [-21500, 2006],
		gapminder_domain: [1800, 1990],
		subngini_domain: [1990, 2023]
	};
	
	static _getNearestCovariateYear (arg0_year) {
		//Convert from parameters
		let target_year = parseInt(arg0_year);
		
		//Declare local instance variables
		let valid_years = landuse_HYDE.sorted_hyde_years;
		
		if (!valid_years || valid_years.length === 0) return target_year;
		
		let nearest_year = valid_years[0];
		let min_diff = Math.abs(target_year - nearest_year);
		
		for (let i = 1; i < valid_years.length; i++) {
			let current_diff = Math.abs(target_year - valid_years[i]);
			if (current_diff < min_diff) {
				min_diff = current_diff;
				nearest_year = valid_years[i];
			}
		}
		
		//Return statement
		return nearest_year;
	}
	
	static _getNearestLandPixel (arg0_lng, arg1_lat) {
		//Convert from parameters
		let lng = parseFloat(arg0_lng);
		let lat = parseFloat(arg1_lat);
		
		//Declare local instance variables
		if (!this.landarea_raster) this.landarea_raster = GeoPNG.loadNumberRasterImage(
			metadata_HYDE.input_raster_land_area, { format: "int32" });
		
		//Return statement
		return Geospatiale.getEquirectangularNearestPixelWith(lng, lat, {
			input_raster: this.landarea_raster,
			special_function: (raster, cx, cy) => {
				let pixel_index = cy*raster.width + cx;
				return (raster.data[pixel_index] > 0);
			}
		});
	}
	
	static getEoscalaGiniObject () {
		//Declare local instance variables
		let gini_array = File.loadCSVAsArray(this.input_gini_premodern_csv, {
			delimiter: ",",
			mode: "vertical"
		});
		let processed_array = [];
		
		//Destructure gini_array into processed_array
		for (let i = 0; i < gini_array.length; i++) {
			//Parse gini_array[i]
			Object.iterate(gini_array[i], (local_key, local_value) => {
				if (local_value === "") {
					delete gini_array[i][local_key];
				} else {
					let local_number = parseFloat(local_value);
					
					if (!isNaN(local_number)) gini_array[i][local_key] = local_number;
				}
			});
			
			let local_coords = [gini_array[i]["Longitude"], gini_array[i]["Latitude"]];
			let local_gini = (gini_array[i]["Income Gini"] || gini_array[i]["Wealth Gini"]); //Historically, these proxy the same thing
				if (local_gini > 1) local_gini = parseFloat(`0.${local_gini}`); //I have no clue why this is happening
			
			//Push to processed_array
			processed_array.push({
				name: gini_array[i]["Site"],
				coords: local_coords,
				gini: local_gini,
				year: gini_array[i]["Year"]
			});
		}
		
		//Return statement
		return processed_array;
	}
	
	static getGapminderGiniObject () {
		//Declare local instance variables
		let csv_obj = File.loadCSVAsJSON(this.input_gini_modern_csv, {
			delimiter: ",",
			mode: "vertical"
		});
		let gini_obj = {};
		
		//Iterate over csv_obj
		Object.iterate(csv_obj, (local_key, local_value) => {
			let local_gini_obj = {};
			
			for (let i = 0; i < local_value.time.length; i++)
				local_gini_obj[local_value.time[i]] = parseFloat(local_value["Gini"][i])/100;
			
			gini_obj[local_key.toUpperCase()] = local_gini_obj;
		});
		
		//Return statement
		return gini_obj;
	}
	
	static getSubNGiniObject () {
		//Return statement
		return JSON.parse(fs.readFileSync(this.input_gini_subngini_json(), "utf8"));
	}
	
	//Eoscala OLS Start
	static async A_loadEoscalaCovariates (arg0_year) {
		//Convert from parameters
		let target_year = arg0_year;
		
		//Declare local instance variables
		let nearest_year = this._getNearestCovariateYear(target_year);
		let raw_points = this.getEoscalaGiniObject();
		let formatted_points = raw_points.map(p => ({
			coords: p.coords,
			target: p.gini,
			year: p.year
		}));
		
		//Return statement
		return Statistics.loadPointOLSCovariates(formatted_points, target_year, {
			covariates_obj: this.covariates_obj,
			covariates_year: nearest_year,
			get_pixel_function: (lng, lat) => this._getNearestLandPixel(lng, lat)
		});
	}
	
	static async A_trainEoscalaModel (arg0_year, arg1_options) {
		//Convert from parameters
		let target_year = parseInt(arg0_year);
		let options = (arg1_options) ? arg1_options : {};
		
		//Initialise options
		if (!options.lambda) options.lambda = 1; //Gini is bounded to [0, 1]
		if (!options.key) options.key = target_year.toString();
		
		//Declare local instance variables
		let covariates_obj = await this.A_loadEoscalaCovariates(target_year);
		
		if (!covariates_obj.X || covariates_obj.X.length === 0) {
			console.warn(`- No valid training points found for year ${target_year}. Skipping OLS.`);
			return null;
		}
		
		let output_file_path = `${this.intermediate_ols_eoscala}/OLS_Eoscala_${target_year}.json`;
		let output_dir = path.dirname(output_file_path);
		
		if (!fs.existsSync(output_dir)) fs.mkdirSync(output_dir, { recursive: true });
		
		//Return statement
		return Statistics.trainOLSModel(output_file_path, covariates_obj, options);
	}
	
	static async A_trainEoscalaModels (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Declare local instance variables
		let formatted_points = [];
		let raw_points = this.getEoscalaGiniObject();
		let unique_years = [];
		
		for (let i = 0; i < raw_points.length; i++) {
			let target_year = parseInt(raw_points[i].year);
			if (!isNaN(target_year) && !unique_years.includes(target_year))
				unique_years.push(target_year);
			formatted_points.push({
				coords: raw_points[i].coords,
				target: raw_points[i].gini,
				year: raw_points[i].year
			});
		}
		
		unique_years.sort((a, b) => a - b);
		console.log(`- Began training for ${unique_years.length} unique years in parallel across background workers.`);
		
		//Return statement
		return await Statistics.trainOLSModelsParallel(unique_years, (target_year) => {
			let all_cov_keys = Object.keys(this.covariates_obj);
			let covariates_map = {};
			let nearest_year = this._getNearestCovariateYear(target_year);
			
			for (let i = 0; i < all_cov_keys.length; i++) {
				let local_key = all_cov_keys[i];
				let local_val = this.covariates_obj[local_key](nearest_year);
				covariates_map[local_key] = local_val;
			}
			
			return {
				covariates_map: covariates_map,
				covariates_year: nearest_year,
				options: {
					...options,
					key: target_year.toString(),
					lambda: (options.lambda !== undefined) ? options.lambda : 1
				},
				output_file_path: `${this.intermediate_ols_eoscala}/OLS_Eoscala_${target_year}.json`,
				points: formatted_points,
				target_year: target_year
			};
		}, {
			concurrency: options.concurrency,
			name: "Gini Eoscala Points OLS Training"
		});
	}
	
	static async A_geomeanEoscalaModel (arg0_prefix) {
		//Convert from parameters
		let prefix = (arg0_prefix) ? arg0_prefix : "OLS_Eoscala_";
		
		//Return statement
		return Statistics.geomeanOLSModels(this.intermediate_ols_eoscala, prefix, {
			weighting_function: (value) => Math.abs(value)
		});
	}
	
	static async A_trainEoscalaOLS (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//1. Train individual yearly OLS models on points
		await this.A_trainEoscalaModels(options);
		
		//2. Compute geomean of yearly models
		try {
			await this.A_geomeanEoscalaModel("OLS_Eoscala_");
		} catch (e) {
			console.error(e);
		}
	}
	//Eoscala OLS End
	
	static async B_trainGapminderOLS (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		if (!options.lambda) options.lambda = 1; //Gini is bounded to [0, 1]
		
		//Declare local instance variables
		let hyde_years = landuse_HYDE.sorted_hyde_years;
		let domain = this.options.gapminder_domain;
		let target_years = hyde_years.filter(y => y >= domain[0] && y <= domain[1]);
		
		let gapminder_obj = this.getGapminderGiniObject();
		let geocode_obj = admin_modern.getISO3ColourcodesObject();
		let geocode_raster = GeoPNG.loadImage(admin_modern.input_geocodes_raster);
		
		let base_dir = this.intermediate_ols_gapminder;
		if (!fs.existsSync(base_dir)) fs.mkdirSync(base_dir, { recursive: true });
		
		//Iterate over target_years to build raster and train OLS models
		for (let i = 0; i < target_years.length; i++) {
			let year = target_years[i];
			let target_raster_path = `${base_dir}gini_target_${year}.png`;
			
			//1. Generate Gini target raster for this year
			GeoPNG.saveNumberRasterImage({
				file_path: target_raster_path,
				format: "float32",
				width: 4320,
				height: 2160,
				function: (local_index) => {
					let byte_index = local_index*4;
					let r = geocode_raster.data[byte_index];
					let g = geocode_raster.data[byte_index + 1];
					let b = geocode_raster.data[byte_index + 2];
					let local_colour_key = `${r},${g},${b}`;
					let local_geocodes = geocode_obj[local_colour_key];
					
					if (local_geocodes) {
						for (let x = 0; x < local_geocodes.length; x++) {
							let country_gini = gapminder_obj[local_geocodes[x]]?.[year];
							if (country_gini !== undefined && !isNaN(country_gini)) {
								return country_gini;
							}
						}
					}
					return 0;
				}
			});
			
			console.log(`Generated target raster for Gapminder OLS: ${target_raster_path}`);
			
			//2. Load covariates and train the model
			let covariates_obj = await Statistics.loadOLSCovariates(target_raster_path, {
				utility_format: "float32",
				covariates_obj: this.covariates_obj,
				formatting_parameters: [year]
			});
			
			if (!covariates_obj.X || covariates_obj.X.length === 0) {
				console.warn(`- No valid pixel samples found for Gapminder year ${year}. Skipping OLS.`);
				continue;
			}
			
			let model_output_path = `${base_dir}OLS_Gapminder_${year}.json`;
			await Statistics.trainOLSModel(model_output_path, covariates_obj, {
				...options,
				lambda: options.lambda,
				key: year.toString()
			});
			
			await Blacktraffic.yield();
		}
		
		//3. Compute geometric mean over the trained Gapminder models
		try {
			await Statistics.geomeanOLSModels(base_dir, "OLS_Gapminder_", {
				weighting_function: (value) => Math.abs(value)
			});
		} catch (e) {
			console.error(`Error calculating geomean for Gapminder models:`, e);
		}
	}
	
	static async C_trainSubNGiniOLS (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		if (!options.lambda) options.lambda = 1; //Gini is bounded to [0, 1]
		
		//Declare local instance variables
		let hyde_years = landuse_HYDE.sorted_hyde_years;
		let domain = this.options.subngini_domain;
		let target_years = hyde_years.filter(y => y >= domain[0] && y <= domain[1]);
		
		let subngini_obj = this.getSubNGiniObject();
		let areal_raster_path = gini_SubNGini.output_areal_raster;
		let areal_raster = GeoPNG.loadImage(areal_raster_path);
		
		let base_dir = this.intermediate_ols_subngini;
		if (!fs.existsSync(base_dir)) fs.mkdirSync(base_dir, { recursive: true });
		
		//1. Pre-evaluate active region keys to ignore always-zero/uninhabited spaces
		let valid_regions = {};
		
		Object.iterate(subngini_obj, (local_key, local_value) => {
			let all_zero = true;
			
			Object.iterate(local_value, (year_key, year_val) => {
				let parsed_val = parseFloat(year_val);
				if (parsed_val !== 0 && !isNaN(parsed_val)) {
					all_zero = false;
				}
			});
			
			if (!all_zero) valid_regions[local_key] = true;
		});
		
		//2. Iterate over target_years to build raster and train OLS models
		for (let i = 0; i < target_years.length; i++) {
			let year = target_years[i];
			let target_raster_path = `${base_dir}gini_target_${year}.png`;
			
			GeoPNG.saveNumberRasterImage({
				file_path: target_raster_path,
				format: "float32",
				width: 4320,
				height: 2160,
				function: (local_index) => {
					let byte_index = local_index * 4;
					let r = areal_raster.data[byte_index];
					let g = areal_raster.data[byte_index + 1];
					let b = areal_raster.data[byte_index + 2];
					let a = areal_raster.data[byte_index + 3];
					let local_colour_key = `${r},${g},${b},${a}`;
					
					if (valid_regions[local_colour_key]) {
						let region_gini = subngini_obj[local_colour_key]?.[year];
						if (region_gini !== undefined && !isNaN(region_gini)) {
							return region_gini;
						}
					}
					return 0;
				}
			});
			
			console.log(`Generated target raster for SubNGini OLS: ${target_raster_path}`);
			
			//3. Load covariates and train the model for this year
			let covariates_obj = await Statistics.loadOLSCovariates(target_raster_path, {
				utility_format: "float32",
				covariates_obj: this.covariates_obj,
				formatting_parameters: [year]
			});
			
			if (!covariates_obj.X || covariates_obj.X.length === 0) {
				console.warn(`- No valid pixel samples found for SubNGini year ${year}. Skipping OLS.`);
				continue;
			}
			
			let model_output_path = `${base_dir}OLS_SubNGini_${year}.json`;
			await Statistics.trainOLSModel(model_output_path, covariates_obj, {
				...options,
				lambda: options.lambda,
				key: year.toString()
			});
			
			await Blacktraffic.yield();
		}
		
		//4. Compute geometric mean over all trained SubNGini yearly models
		try {
			await Statistics.geomeanOLSModels(base_dir, "OLS_SubNGini_", {
				weighting_function: (value) => Math.abs(value)
			});
		} catch (e) {
			console.error(`Error calculating geomean for SubNGini models:`, e);
		}
	}
	
	static async processRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		if (!options.exclude) options.exclude = [];
		if (options.skip_training || options.use_existing_models || options.train === false) {
			console.log(`[gini_OLS] Skipping training (using existing models).`);
			return;
		}
		
		if (!options.exclude.includes("A")) await this.A_trainEoscalaOLS(options);
		if (!options.exclude.includes("B")) await this.B_trainGapminderOLS(options);
		if (!options.exclude.includes("C")) await this.C_trainSubNGiniOLS(options);
	}
};