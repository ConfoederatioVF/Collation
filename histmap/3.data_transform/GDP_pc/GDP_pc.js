global.GDP_pc = class {
	static cf = `${h3}/GDP_pc/`;
	static input_covariates_obj = () => {
		let covariates_obj = {
			...GDP_PPP_SEDAC.covariates_obj,
			//Demographics: Retain urban and rural counts to model urban agglomeration and productivity premium
			"popd_": (y) => [`${this.sf().intermediate_popd_folder}/stadester_density_${y}.png`, "float32"],
			"rurc_": (y) => [`${this.sf().input_rurc_folder}/stadester_rural_${y}.png`, "float32"],
			"urbc_": (y) => [`${this.sf().input_urbc_folder}/stadester_urban_${y}.png`, "float32"]
		};
		
		//Return statement
		return covariates_obj;
	};
	static input_gdp_pc_folder = `${this.cf}rasters/`;
	static intermediate_ols_folder = `${this.cf}1.OLS/`;
	static intermediate_ols_rasters_folder = `${this.cf}2.OLS_pc_estimates/`;
	static intermediate_pc_estimates_folder = `${this.cf}3.pc_estimates/`;
	static intermediate_gdp_folder = `${this.cf}/4.GDP_rasters/`;
	static intermediate_gdp_scaled_to_global = `${this.cf}/5.scaled_to_global/`;
	static intermediate_gdp_interpolated = `${this.cf}/6.interpolated/`;
	static intermediate_gdp_scaled_to_national = GDP_nominal.intermediate_scaled_to_national;
	static output_gdp_pc_folder = `${this.cf}/8.GDP_nominal_pc_rasters/`;
	
	//HYDE; Stadestér formatters
	static hf = () => `${landuse_HYDE.bf}/rasters/`;
	static hf1 = (y) => landuse_HYDE._getHYDEYearName(y);
	static sf = () => population_Stadester;
	
	static async A_generateGDP_pcRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Declare local instance variables
		let hyde_years = landuse_HYDE.sorted_hyde_years;
		let out_dir = (typeof path !== "undefined") ? path.resolve(this.input_gdp_pc_folder) : this.input_gdp_pc_folder;
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
		let target_years = [];
		
		let geocode_obj = admin_modern.getISO3ColourcodesObject();
		let geocodes_raster_path = admin_modern.input_geocodes_raster;
		let gdp_obj = GDP_nominal.getGDPObject();
		
		if (!fs.existsSync(out_dir)) fs.mkdirSync(out_dir, { recursive: true });
		
		for (let i = 0; i < hyde_years.length; i++) {
			let local_output_path = `${this.input_gdp_pc_folder}GDP_pc_${hyde_years[i]}.png`;
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
			name: "GDP_pc A_generateGDP_pcRasters (Uniform Historical Target)",
			handler: async (year) => {
				let local_output_path = `${this.input_gdp_pc_folder}GDP_pc_${year}.png`;
				let local_popc_path = `${population_Stadester.input_popc_folder}stadester_population_${year}.png`;
				
				let local_popc_raster = GeoPNG.loadNumberRasterImage(local_popc_path, { format: "float32" });
				let geocode_raster = GeoPNG.loadImage(geocodes_raster_path);
				
				let national_pop_sums = {};
				
				// 1. Calculate national populations
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
				
				// 2. Assign uniform per-capita figures
				GeoPNG.saveNumberRasterImage({
					file_path: local_output_path,
					format: "float32",
					width: 4320,
					height: 2160,
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
									return target_gdp / target_pop;
								}
							}
						}
						return 0;
					}
				});
			}
		});
	}
	
	static async B_loadCovariates (arg0_year) {
		//Convert from parameters
		let year = arg0_year;
		
		//Declare local instance variables
		let input_file_path = `${this.input_gdp_pc_folder}/GDP_pc_${year}.png`;
		
		//Return statement
		return Statistics.loadOLSCovariates(input_file_path, {
			utility_format: "float32",
			
			covariates_obj: this.input_covariates_obj(),
			formatting_parameters: [year]
		});
	}
	
	static async B_trainGDP_pcModel (arg0_year, arg1_options) {
		//Convert from parameters
		let year = parseInt(arg0_year);
		let options = (arg1_options) ? arg1_options : {};
		
		//Initialise options
		if (!options.key) options.key = year.toString();
		if (!options.lambda) options.lambda = 1e6;
		if (!options.weighting_function) options.weighting_function = (value) => Math.abs(value);
		
		//Declare local instance variables
		let covariates_obj = await this.B_loadCovariates(year);
		let output_file_path =  `${this.intermediate_ols_folder}/OLS_GDP_pc_${year}.json`;
		
		//Return statement
		return Statistics.trainOLSModel(output_file_path, covariates_obj, options);
	}
	
	static async B_trainGDP_pcModels (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Declare local instance variables
		let years = landuse_HYDE.sorted_hyde_years;
		
		// 1. Train models
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
					lambda: Math.returnSafeNumber(options.lambda, 1e6),
					weight_file_path: `${population_Stadester.input_popc_folder}stadester_population_${year}.png`,
					weighting_function: (value) => Math.abs(value)
				},
				output_file_path: `${this.intermediate_ols_folder}OLS_GDP_pc_${year}.json`,
				target_file_path: `${this.input_gdp_pc_folder}GDP_pc_${year}.png`,
				target_format: "float32"
			};
		}, {
			concurrency: options.concurrency || 8,
			name: "GDP_pc 2nd-pass OLS Training"
		});
		
		// 2. Identify invalid models (all coefficients are 0) and temporarily rename them so they aren't averaged
		let invalid_years = [];
		for (let i = 0; i < years.length; i++) {
			let file_path = `${this.intermediate_ols_folder}OLS_GDP_pc_${years[i]}.json`;
			if (fs.existsSync(file_path)) {
				let model_data = JSON.parse(fs.readFileSync(file_path, "utf8"));
				let sum_coeffs = 0;
				for (let key in model_data.coefficients) {
					sum_coeffs += Math.abs(model_data.coefficients[key]);
				}
				if (sum_coeffs === 0) {
					invalid_years.push(years[i]);
					fs.renameSync(file_path, `${this.intermediate_ols_folder}INVALID_OLS_GDP_pc_${years[i]}.json`);
				}
			}
		}
		
		// 3. Compute geometric average of valid OLS models
		let geomean_data = await Statistics.geomeanOLSModels(this.intermediate_ols_folder, "OLS_GDP_pc_");
		
		// 4. Restore and overwrite invalid models with the geomean
		for (let i = 0; i < invalid_years.length; i++) {
			let invalid_path = `${this.intermediate_ols_folder}INVALID_OLS_GDP_pc_${invalid_years[i]}.json`;
			let target_path = `${this.intermediate_ols_folder}OLS_GDP_pc_${invalid_years[i]}.json`;
			
			if (fs.existsSync(invalid_path)) {
				let invalid_data = JSON.parse(fs.readFileSync(invalid_path, "utf8"));
				invalid_data.coefficients = geomean_data.coefficients;
				fs.writeFileSync(target_path, JSON.stringify(invalid_data, null, 2));
				fs.unlinkSync(invalid_path);
			}
		}
	}
	
	static async C_generateOLS_GDP_pcRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Declare local instance variables
		let hyde_years = landuse_HYDE.sorted_hyde_years;
		let out_dir = (typeof path !== "undefined") ? path.resolve(this.intermediate_ols_rasters_folder) : this.intermediate_ols_rasters_folder;
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
		let target_years = [];
		
		if (!fs.existsSync(out_dir)) fs.mkdirSync(out_dir, { recursive: true });
		
		for (let i = 0; i < hyde_years.length; i++) {
			let local_input_path = `${this.intermediate_ols_folder}OLS_GDP_pc_${hyde_years[i]}.json`;
			let local_output_path = `${this.intermediate_ols_rasters_folder}OLS_GDP_pc_${hyde_years[i]}.png`;
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
				model_obj: `${this.intermediate_ols_folder}OLS_GDP_pc_${year}.json`,
				options: {
					format: "float32"
				},
				output_file_path: `${this.intermediate_ols_rasters_folder}OLS_GDP_pc_${year}.png`
			};
		}, {
			concurrency: options.concurrency || 8,
			name: "GDP_pc OLS Raster Generation"
		});
	}
	
	static async D_normaliseGDP_pcRasters (arg0_options) {
		let options = (arg0_options) ? arg0_options : {};
		let years = landuse_HYDE.sorted_hyde_years;
		let landarea_file = metadata_HYDE.input_raster_land_area;
		let landarea_raster = GeoPNG.loadNumberRasterImage(landarea_file, { format: "int32" });
		
		let thresholds = {};
		let global_prev_max = 0;
		
		// 1. Fast sequential pre-pass to calculate limits
		console.log(`[GDP_pc] Running fast sequential pre-pass for Step D thresholds...`);
		let final_year = years[years.length - 1];
		let first_pass_path = `${this.input_gdp_pc_folder}GDP_pc_${final_year}.png`;
		
		if (fs.existsSync(first_pass_path)) {
			let first_pass_raster = GeoPNG.loadNumberRasterImage(first_pass_path, { format: "float32" });
			let final_max = -Infinity;
			for (let x = 0; x < first_pass_raster.data.length; x++) {
				let fp_val = first_pass_raster.data[x];
				if (isFinite(fp_val) && fp_val > final_max) final_max = fp_val;
			}
			if (isFinite(final_max) && final_max > 0) global_prev_max = final_max;
		}
		
		for (let i = 0; i < years.length; i++) {
			thresholds[years[i]] = global_prev_max;
		}
		
		// 2. Parallel raster generation
		await GeoPNG.processTimeseriesParallel({
			concurrency: options.concurrency || 8,
			items: years,
			name: "GDP_pc D_normaliseGDP_pcRasters",
			handler: async (year) => {
				if (!thresholds[year]) return null;
				let prev_max = thresholds[years[Math.max(0, years.indexOf(year) - 1)]] || 0;
				
				let first_pass_path = `${this.input_gdp_pc_folder}GDP_pc_${year}.png`;
				let second_pass_path = `${this.intermediate_ols_rasters_folder}OLS_GDP_pc_${year}.png`;
				let pop_path = `${population_Stadester.input_popc_folder}stadester_population_${year}.png`;
				let output_path = `${this.intermediate_pc_estimates_folder}GDP_pc_${year}.png`;
				
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
					data: second_pass_raster.data, fraction_only: true, valid_filter: (x) => landarea_raster.data[x] > 0 && pop_raster.data[x] >= 1.0
				});
				
				GeoPNG.saveNumberRasterImage({
					file_path: output_path, format: "float32", height: 2160, width: 4320,
					function: (local_index) => {
						if (landarea_raster.data[local_index] === 0 || pop_raster.data[local_index] < 1.0) return 0;
						let fp_val = first_pass_raster.data[local_index];
						if (!isFinite(fp_val) || fp_val < 0) fp_val = 0;
						let sp_frac = second_pass_fractions[local_index];
						if (!isFinite(sp_frac) || sp_frac < 0) sp_frac = 0;
						let res = fp_val + (first_pass_range * sp_frac);
						
						if (years.indexOf(year) > 0 && prev_max > 0) {
							let cap = prev_max * 10;
							if (res > cap) res = cap + prev_max * Math.log(1 + ((res - cap) / prev_max));
						}
						return (isFinite(res) && res > 0 && res < 3.402823466e38) ? res : 0;
					}
				});
				console.log(`- Saved ${output_path}. Max observed: ${thresholds[year]}`);
			}
		});
	}
	
	static async E_generateGDPRasters () {
		//Declare local instance variables
		let years = landuse_HYDE.sorted_hyde_years;
		
		await GeoPNG.processTimeseriesParallel({
			concurrency: 8,
			items: years,
			name: "GDP_pc E_generateGDPRasters",
			task_generator: (year) => {
				let pc_path = `${this.intermediate_pc_estimates_folder}GDP_pc_${year}.png`;
				let pop_path = `${population_Stadester.input_popc_folder}stadester_population_${year}.png`;
				let output_path = `${this.intermediate_gdp_folder}GDP_${year}.png`;
				
				if (!fs.existsSync(pc_path) || !fs.existsSync(pop_path)) return null;
				
				return {
					type: "raster_operation",
					format1: "float32",
					format2: "float32",
					input_path_1: pc_path,
					input_path_2: pop_path,
					op: "multiply",
					output_format: "float32",
					output_path: output_path
				};
			},
			handler: async (year) => {
				let pc_path = `${this.intermediate_pc_estimates_folder}GDP_pc_${year}.png`;
				let pop_path = `${population_Stadester.input_popc_folder}stadester_population_${year}.png`;
				let output_path = `${this.intermediate_gdp_folder}GDP_${year}.png`;
				
				if (fs.existsSync(pc_path) && fs.existsSync(pop_path)) {
					let pc_raster = GeoPNG.loadNumberRasterImage(pc_path, { format: "float32" });
					let pop_raster = GeoPNG.loadNumberRasterImage(pop_path, { format: "float32" });
					
					GeoPNG.saveNumberRasterImage({
						file_path: output_path,
						format: "float32",
						height: 2160,
						width: 4320,
						function: (local_index) => pc_raster.data[local_index]*pop_raster.data[local_index]
					});
					console.log(`- Saved total GDP: ${output_path}`);
				}
			}
		});
	}
	
	static async F_scaleGDPRastersToGlobal () {
		//Return statement; Reusing logic from GDP_nominal core class
		return GDP_nominal.A_scaleGDPRastersToGlobal(
			this.intermediate_gdp_folder,
			this.intermediate_gdp_scaled_to_global
		);
	}
	
	static async G_interpolateToSEDAC (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Declare local instance variables
		let hyde_years = landuse_HYDE.sorted_hyde_years;
		let out_dir = (typeof path !== "undefined") ? path.resolve(this.intermediate_gdp_interpolated) : this.intermediate_gdp_interpolated;
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
		let sedac_domain = [1800, 1990];
		let sedac1_domain = [1800, 1950];
		let sedac2_domain = [1950, 1990];
		let target_years = [];
		let template_path = `${GDP_nominal_SEDAC.bf}GDP_2022.png`;
		let template_sum = 0;
		if (fs.existsSync(template_path))
			template_sum = GeoPNG.getImageSum(template_path, { format: "float32" });
		let to_path = `${GDP_nominal_SEDAC.bf}GDP_1990.png`;
		let world_gdp_obj = GDP_nominal.getWorldGDPObject();
		let year_gap = sedac_domain[1] - sedac_domain[0];
		let year_gap2 = sedac2_domain[1] - sedac2_domain[0];
		
		if (!fs.existsSync(out_dir)) fs.mkdirSync(out_dir, { recursive: true });
		
		for (let i = 0; i < hyde_years.length; i++) {
			let local_output_path = `${this.intermediate_gdp_interpolated}GDP_${hyde_years[i]}.png`;
			if (overwrite || !fs.existsSync(local_output_path))
				target_years.push(hyde_years[i]);
		}
		
		if (target_years.length === 0) return [];
		
		//Return statement
		return GeoPNG.processTimeseriesParallel({
			concurrency: options.concurrency || 8,
			items: target_years,
			name: "GDP_pc G_interpolateToSEDAC",
			task_generator: (current_year) => {
				let local_from_path = `${this.intermediate_gdp_scaled_to_global}GDP_${current_year}.png`;
				let local_output_path = `${this.intermediate_gdp_interpolated}GDP_${current_year}.png`;
				
				if (current_year < sedac_domain[0]) {
					return {
						dest_path: local_output_path,
						source_path: local_from_path,
						type: "copy"
					};
				} else if (current_year >= sedac_domain[0] && current_year < sedac_domain[1]) {
					let fraction = (current_year - sedac_domain[0])/year_gap;
					let interp_options = { format: "float32", fraction: fraction };
					if (current_year < sedac1_domain[1]) {
						interp_options.upper_value_threshold = 256;
					} else {
						interp_options.threshold_fraction = (current_year - sedac2_domain[0])/year_gap2;
					}
					
					return {
						from_file_path: local_from_path,
						options: interp_options,
						output_file_path: local_output_path,
						to_file_path: to_path,
						type: "linear_interpolation"
					};
				} else if (current_year >= 1990 && current_year <= 2022) {
					let local_sedac_path = `${GDP_nominal_SEDAC.bf}GDP_${current_year}.png`;
					return {
						dest_path: local_output_path,
						source_path: local_sedac_path,
						type: "copy"
					};
				} else {
					if (fs.existsSync(template_path)) {
						let target_global = Math.returnSafeNumber(world_gdp_obj[current_year], template_sum);
						let global_scalar = (template_sum > 0) ? target_global/template_sum : 1;
						return {
							format: "float32",
							input_path_1: template_path,
							output_path: local_output_path,
							scalar: global_scalar,
							type: "raster_operation"
						};
					}
				}
				return null;
			},
			handler: async (current_year) => {
				let local_from_path = `${this.intermediate_gdp_scaled_to_global}GDP_${current_year}.png`;
				let local_output_path = `${this.intermediate_gdp_interpolated}GDP_${current_year}.png`;
				
				if (current_year < sedac_domain[0]) {
					if (fs.existsSync(local_from_path)) {
						fs.copyFileSync(local_from_path, local_output_path);
						console.log(`- Copying global scaled GDP directly for year ${current_year}.`);
					}
				} else if (current_year >= sedac_domain[0] && current_year < sedac_domain[1]) {
					let fraction = (current_year - sedac_domain[0])/year_gap;
					
					if (current_year < sedac1_domain[1]) {
						GeoPNG.linearInterpolation(local_from_path, to_path, local_output_path, {
							format: "float32",
							fraction: fraction,
							upper_value_threshold: 256
						});
					} else {
						let threshold_fraction = (current_year - sedac2_domain[0])/year_gap2;
						GeoPNG.linearInterpolation(local_from_path, to_path, local_output_path, {
							format: "float32",
							fraction: fraction,
							threshold_fraction: threshold_fraction
						});
					}
				} else if (current_year >= 1990 && current_year <= 2022) {
					let local_sedac_path = `${GDP_nominal_SEDAC.bf}GDP_${current_year}.png`;
					if (fs.existsSync(local_sedac_path)) {
						fs.copyFileSync(local_sedac_path, local_output_path);
						console.log(`- Copying SEDAC template directly for year ${current_year}.`);
					}
				} else {
					let template_path = `${GDP_nominal_SEDAC.bf}GDP_2022.png`;
					if (fs.existsSync(template_path)) {
						let template_raster = GeoPNG.loadNumberRasterImage(template_path, { format: "float32" });
						let template_sum = GeoPNG.getImageSum(template_path, { format: "float32" });
						let target_global = Math.returnSafeNumber(world_gdp_obj[current_year], template_sum);
						let global_scalar = target_global/template_sum;
						
						GeoPNG.saveNumberRasterImage({
							file_path: local_output_path,
							format: "float32",
							width: 4320,
							height: 2160,
							function: (local_index) => template_raster.data[local_index]*global_scalar
						});
					}
				}
			}
		});
	}
	
	static async H_scaleGDPRastersToNational (arg0_options) {
		let options = (arg0_options) ? arg0_options : {};
		let hyde_years = landuse_HYDE.sorted_hyde_years;
		let gdp_obj = GDP_nominal.getGDPObject();
		let geocode_obj = admin_modern.getISO3ColourcodesObject();
		let geocode_raster = GeoPNG.loadImage(admin_modern.input_geocodes_raster);
		let previous_max_pc = 0;
		let thresholds = {};
		
		console.log(`[GDP_pc] Running fast sequential pre-pass for Step H thresholds...`);
		for (let i = 0; i < hyde_years.length; i++) {
			let current_year = hyde_years[i];
			let local_input_file_path = `${this.intermediate_gdp_interpolated}GDP_${current_year}.png`;
			if (!fs.existsSync(local_input_file_path)) continue;
			
			let local_input_raster = GeoPNG.loadNumberRasterImage(local_input_file_path, { format: "float32" });
			let local_popc_file_path = `${population_Stadester.input_popc_folder}stadester_population_${current_year}.png`;
			let local_popc_raster = GeoPNG.loadNumberRasterImage(local_popc_file_path, { format: "float32" });
			
			let local_gdp_sums = {};
			let country_stats = {};
			let current_max_pc = 0;
			let local_threshold = (previous_max_pc > 0) ? Math.min(previous_max_pc * 4, 500000) : 500000;
			let clamp_alpha = local_threshold * 0.1;
			
			for (let x = 0; x < local_input_raster.data.length; x++) {
				let byte_index = x * 4;
				let local_colour_key = `${geocode_raster.data[byte_index]},${geocode_raster.data[byte_index+1]},${geocode_raster.data[byte_index+2]}`;
				let local_geocodes = geocode_obj[local_colour_key];
				if (local_geocodes)
					for (let y = 0; y < local_geocodes.length; y++)
						Object.modifyValue(local_gdp_sums, local_geocodes[y], local_input_raster.data[x]);
			}
			
			Object.iterate(local_gdp_sums, (local_key, local_value) => {
				let local_target = gdp_obj[local_key]?.[current_year];
				country_stats[local_key] = {
					initial_scalar: (local_target) ? local_target / local_value : 1, outlier_gdp: 0, remaining_input_sum: 0, target_gdp: local_target || local_value
				};
			});
			
			for (let x = 0; x < local_input_raster.data.length; x++) {
				let local_val = local_input_raster.data[x];
				if (local_val === 0) continue;
				let byte_index = x * 4;
				let local_colour_key = `${geocode_raster.data[byte_index]},${geocode_raster.data[byte_index+1]},${geocode_raster.data[byte_index+2]}`;
				let local_geocodes = geocode_obj[local_colour_key];
				
				if (local_geocodes && local_geocodes.length > 0) {
					let stats = country_stats[local_geocodes[0]];
					if (stats) {
						let local_pop = local_popc_raster.data[x];
						let raw_pc = (local_pop >= 1.0) ? (local_val * stats.initial_scalar) / local_pop : 0;
						if (raw_pc > local_threshold) {
							let reg_pc = local_threshold + clamp_alpha * Math.log(1 + ((raw_pc - local_threshold) / clamp_alpha));
							stats.outlier_gdp += reg_pc * local_pop;
						} else {
							stats.remaining_input_sum += local_val;
						}
					}
				}
			}
			
			Object.iterate(country_stats, (country_code, stats) => {
				let remaining_target = Math.max(0, stats.target_gdp - stats.outlier_gdp);
				stats.secondary_scalar = (stats.remaining_input_sum > 0) ? remaining_target / stats.remaining_input_sum : stats.initial_scalar;
			});
			
			for (let x = 0; x < local_input_raster.data.length; x++) {
				let local_val = local_input_raster.data[x];
				if (local_val === 0) continue;
				let byte_index = x * 4;
				let local_colour_key = `${geocode_raster.data[byte_index]},${geocode_raster.data[byte_index+1]},${geocode_raster.data[byte_index+2]}`;
				let local_geocodes = geocode_obj[local_colour_key];
				
				let final_val = local_val;
				if (local_geocodes && local_geocodes.length > 0) {
					let stats = country_stats[local_geocodes[0]];
					if (stats) {
						let local_pop = local_popc_raster.data[x];
						let raw_pc = (local_pop >= 1.0) ? (local_val * stats.initial_scalar) / local_pop : 0;
						if (raw_pc > local_threshold) {
							let reg_pc = local_threshold + clamp_alpha * Math.log(1 + ((raw_pc - local_threshold) / clamp_alpha));
							final_val = reg_pc * local_pop;
						} else {
							let res_pc = (local_pop >= 1.0) ? (local_val * stats.secondary_scalar) / local_pop : 0;
							if (res_pc > local_threshold) {
								let reg_pc = local_threshold + clamp_alpha * Math.log(1 + ((res_pc - local_threshold) / clamp_alpha));
								final_val = reg_pc * local_pop;
							} else final_val = local_val * stats.secondary_scalar;
						}
					}
				}
				
				let pop = local_popc_raster.data[x];
				if (pop >= 1.0) {
					let pc = final_val / pop;
					if (isFinite(pc) && pc > current_max_pc) current_max_pc = pc;
				}
			}
			
			// Dasymetric blur doesn't increase max PC significantly, so we can ignore it for threshold calc
			if (current_max_pc > 0) previous_max_pc = current_max_pc;
			thresholds[current_year] = { max: current_max_pc, threshold: local_threshold, stats: country_stats };
		}
		
		await GeoPNG.processTimeseriesParallel({
			concurrency: options.concurrency || 8,
			items: hyde_years,
			name: "GDP_pc H_scaleGDPRastersToNational",
			handler: async (year) => {
				if (!thresholds[year]) return null;
				let { threshold, stats } = thresholds[year];
				let local_input_file_path = `${this.intermediate_gdp_interpolated}GDP_${year}.png`;
				let local_input_raster = GeoPNG.loadNumberRasterImage(local_input_file_path, { format: "float32" });
				let local_popc_file_path = `${population_Stadester.input_popc_folder}stadester_population_${year}.png`;
				let local_popc_raster = GeoPNG.loadNumberRasterImage(local_popc_file_path, { format: "float32" });
				let local_output_file = `${this.intermediate_gdp_scaled_to_national}GDP_${year}.png`;
				
				let clamp_alpha = threshold * 0.1;
				let raw_scaled_data = new Float32Array(4320 * 2160);
				
				for (let local_index = 0; local_index < local_input_raster.data.length; local_index++) {
					let local_val = local_input_raster.data[local_index];
					if (local_val === 0) continue;
					let byte_index = local_index * 4;
					let local_colour_key = `${geocode_raster.data[byte_index]},${geocode_raster.data[byte_index+1]},${geocode_raster.data[byte_index+2]}`;
					let local_geocodes = geocode_obj[local_colour_key];
					
					if (local_geocodes && local_geocodes.length > 0) {
						let s = stats[local_geocodes[0]];
						if (s) {
							let local_pop = local_popc_raster.data[local_index];
							let raw_pc = (local_pop >= 1.0) ? (local_val * s.initial_scalar) / local_pop : 0;
							
							if (raw_pc > threshold) {
								let reg_pc = threshold + clamp_alpha * Math.log(1 + ((raw_pc - threshold) / clamp_alpha));
								raw_scaled_data[local_index] = reg_pc * local_pop;
							} else {
								let result_gdp = local_val * s.secondary_scalar;
								let result_pc = (local_pop >= 1.0) ? result_gdp / local_pop : 0;
								if (result_pc > threshold) {
									let reg_pc = threshold + clamp_alpha * Math.log(1 + ((result_pc - threshold) / clamp_alpha));
									raw_scaled_data[local_index] = reg_pc * local_pop;
								} else raw_scaled_data[local_index] = result_gdp;
							}
						} else raw_scaled_data[local_index] = local_val;
					} else raw_scaled_data[local_index] = local_val;
				}
				
				let final_data = raw_scaled_data;
				if (year > 0 && year < 1800) {
					let pc_data = new Float32Array(4320 * 2160);
					for (let j = 0; j < 4320 * 2160; j++) {
						if (local_popc_raster.data[j] >= 1.0) pc_data[j] = raw_scaled_data[j] / local_popc_raster.data[j];
					}
					let blurred_pc = GeoPNG.dasymetricBlur({
						mask_data: geocode_raster.data, pop_data: local_popc_raster.data, target_data: pc_data, height: 2160, width: 4320, radius: 64
					});
					final_data = new Float32Array(4320 * 2160);
					for (let j = 0; j < 4320 * 2160; j++) final_data[j] = blurred_pc[j] * local_popc_raster.data[j];
				}
				
				GeoPNG.saveNumberRasterImage({
					file_path: local_output_file, format: "float32", height: 2160, width: 4320,
					function: (local_index) => {
						let val = final_data[local_index];
						return (isFinite(val) && val < 3.402823466e38) ? val : 0;
					}
				});
				console.log(`- Finished GDP ${year}. Healthy max PC: ${thresholds[year].max} (Threshold: ${threshold})`);
			}
		});
	}
	
	static async I_recalculateGDP_pcRasters (arg0_options) {
		let options = (arg0_options) ? arg0_options : {};
		let hyde_years = landuse_HYDE.sorted_hyde_years;
		let previous_max_pc = 0;
		let thresholds = {};
		
		console.log(`[GDP_pc] Running fast sequential pre-pass for Step I thresholds...`);
		for (let i = 0; i < hyde_years.length; i++) {
			let current_year = hyde_years[i];
			let total_file_path = `${this.intermediate_gdp_scaled_to_national}GDP_${current_year}.png`;
			let popc_file_path = `${population_Stadester.input_popc_folder}stadester_population_${current_year}.png`;
			
			if (fs.existsSync(total_file_path) && fs.existsSync(popc_file_path)) {
				let total_raster = GeoPNG.loadNumberRasterImage(total_file_path, { format: "float32" });
				let popc_raster = GeoPNG.loadNumberRasterImage(popc_file_path, { format: "float32" });
				
				let current_max_pc = 0;
				let local_threshold = (previous_max_pc > 0) ? Math.min(previous_max_pc * 4, 500000) : 500000;
				let clamp_alpha = local_threshold * 0.1;
				
				for (let local_index = 0; local_index < total_raster.data.length; local_index++) {
					let local_pop = popc_raster.data[local_index];
					if (local_pop < 1.0) continue;
					let local_pc = total_raster.data[local_index] / local_pop;
					if (isFinite(local_pc)) {
						if (local_pc > local_threshold) local_pc = local_threshold + clamp_alpha * Math.log(1 + ((local_pc - local_threshold) / clamp_alpha));
						if (local_pc > current_max_pc) current_max_pc = local_pc;
					}
				}
				
				if (current_max_pc > 0) previous_max_pc = current_max_pc;
				thresholds[current_year] = { max: current_max_pc, threshold: local_threshold };
			}
		}
		
		await GeoPNG.processTimeseriesParallel({
			concurrency: options.concurrency || 8,
			items: hyde_years,
			name: "GDP_pc I_recalculateGDP_pcRasters",
			handler: async (year) => {
				if (!thresholds[year]) return null;
				let threshold = thresholds[year].threshold;
				let max = thresholds[year].max;
				let total_file_path = `${this.intermediate_gdp_scaled_to_national}GDP_${year}.png`;
				let popc_file_path = `${population_Stadester.input_popc_folder}stadester_population_${year}.png`;
				let output_file_path = `${this.output_gdp_pc_folder}GDP_pc_${year}.png`;
				
				let total_raster = GeoPNG.loadNumberRasterImage(total_file_path, { format: "float32" });
				let popc_raster = GeoPNG.loadNumberRasterImage(popc_file_path, { format: "float32" });
				let clamp_alpha = threshold * 0.1;
				
				GeoPNG.saveNumberRasterImage({
					file_path: output_file_path, format: "float32", width: 4320, height: 2160,
					function: (local_index) => {
						let local_pop = popc_raster.data[local_index];
						if (local_pop < 1.0) return 0;
						let local_pc = total_raster.data[local_index] / local_pop;
						if (!isFinite(local_pc)) return 0;
						
						if (local_pc > threshold) {
							local_pc = threshold + clamp_alpha * Math.log(1 + ((local_pc - threshold) / clamp_alpha));
						}
						return (isFinite(local_pc) && local_pc < 3.402823466e38) ? local_pc : 0;
					}
				});
				console.log(`- Recalculated PC for ${year}. Healthy max: ${max}`);
			}
		});
	}
	
	static async processRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		if (!options.exclude) options.exclude = [];
		if (options.skip_training || options.use_existing_models || options.train === false) {
			if (!options.exclude.includes("B")) options.exclude.push("B");
			console.log(`[GDP_pc] Skipping Step B 2nd-pass OLS training (using existing models).`);
		}
		
		//1. Generate GDP_pc rasters
		if (!options.exclude.includes("A")) await this.A_generateGDP_pcRasters(options);
		//2. 2nd-pass OLS training
		if (!options.exclude.includes("B")) await this.B_trainGDP_pcModels(options);
		if (!options.exclude.includes("C")) await this.C_generateOLS_GDP_pcRasters(options);
		if (!options.exclude.includes("D")) await this.D_normaliseGDP_pcRasters();
		
		//3. Ensemble regeneration and scaling
		if (!options.exclude.includes("E")) await this.E_generateGDPRasters();
		if (!options.exclude.includes("F")) await this.F_scaleGDPRastersToGlobal(options);
		if (!options.exclude.includes("G")) await this.G_interpolateToSEDAC(options);
		if (!options.exclude.includes("H")) await this.H_scaleGDPRastersToNational();
		
		//4. Final top-down constraint recalculation
		if (!options.exclude.includes("I")) await this.I_recalculateGDP_pcRasters();
	}
};