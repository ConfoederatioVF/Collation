global.LFPR_OLS = class {
	static bf = `${h2}/LFPR_OLS/`;
	
	// Paths
	static intermediate_ols_models = `${this.bf}/0.OLS_models/`;
	static intermediate_ols_rasters = `${this.bf}/1.OLS_rasters/`;
	static intermediate_normalised_rasters = `${this.bf}/2.normalised_rasters/`;
	static output_lfpr_rates = `${this.bf}/3.lfpr_rates/`;
	static output_active_labourforce = `${this.bf}/4.active_labourforce/`;
	
	static sexes = ["f", "m"];
	static working_cohorts = ["15", "20", "25", "30", "35", "40", "45", "50", "55", "60", "65", "70", "75", "80"];
	
	// Utilise demographic parameters and structural inequality (gini) as covariates
	static covariates_obj = () => ({
		...age_sex.covariates_obj,
		"gini": (y) => [`${gini_Eoscala.output_rasters}gini_${y}.png`, "float32"]
	});
	
	/**
	 * TRAIN: Train OLS models using the LFPR_Olivetti targets.
	 */
	static async A_trainOLSModels (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		let lambda_val = (options.lambda !== undefined) ? options.lambda : 1;
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
		
		//Declare local instance variables
		let covariates_obj = this.covariates_obj();
		let years = landuse_HYDE.sorted_hyde_years;
		
		if (!fs.existsSync(this.intermediate_ols_models)) fs.mkdirSync(this.intermediate_ols_models, { recursive: true });
		
		for (let s = 0; s < this.sexes.length; s++) {
			let sex = this.sexes[s];
			let target_years = years.filter((year) => {
				let target_path = `${LFPR_Olivetti.intermediate_rasters_folder}lfpr_${sex}_${year}.png`;
				let model_path = `${this.intermediate_ols_models}OLS_lfpr_${sex}_${year}.json`;
				if (!fs.existsSync(target_path)) return false;
				if (!overwrite && fs.existsSync(model_path)) return false;
				return true;
			});
			
			if (target_years.length > 0) {
				await Statistics.trainOLSModelsParallel(target_years, (year) => {
					let all_cov_keys = Object.keys(covariates_obj);
					let covariates_map = {};
					let format_year = Math.min(year, 2023);
					for (let i = 0; i < all_cov_keys.length; i++) {
						let local_key = all_cov_keys[i];
						let local_val = covariates_obj[local_key](format_year);
						covariates_map[local_key] = local_val;
					}
					
					return {
						covariates_map: covariates_map,
						options: {
							...options,
							key: year.toString(),
							lambda: lambda_val
						},
						output_file_path: `${this.intermediate_ols_models}OLS_lfpr_${sex}_${year}.json`,
						target_file_path: `${LFPR_Olivetti.intermediate_rasters_folder}lfpr_${sex}_${year}.png`,
						target_format: "float32"
					};
				}, {
					concurrency: options.concurrency,
					name: `LFPR OLS Training (${sex})`
				});
			}
			
			// Generate the generalized geomean model for the current sex
			try {
				await Statistics.geomeanOLSModels(this.intermediate_ols_models, `OLS_lfpr_${sex}_`, {
					weighting_function: (value) => Math.abs(value)
				});
				console.log(`- Generated Geomean OLS model for ${sex}`);
			} catch (e) {
				console.error(`Error calculating geomean for LFPR models (sex ${sex}):`, e);
			}
		}
	}
	
	static async B_generateOLSRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
		
		//Declare local instance variables
		let covariates_obj = this.covariates_obj();
		let years = landuse_HYDE.sorted_hyde_years;
		
		if (!fs.existsSync(this.intermediate_ols_rasters)) fs.mkdirSync(this.intermediate_ols_rasters, { recursive: true });
		
		for (let s = 0; s < this.sexes.length; s++) {
			let sex = this.sexes[s];
			let unified_model_path = `${this.intermediate_ols_models}geomean_OLS_lfpr_${sex}.json`;
			if (!fs.existsSync(unified_model_path)) continue;
			
			let target_years = years.filter((year) => {
				let output_path = `${this.intermediate_ols_rasters}ols_lfpr_${sex}_${year}.png`;
				return (overwrite || !fs.existsSync(output_path));
			});
			
			if (target_years.length > 0) {
				await Statistics.generateOLSRastersParallel(target_years, (year) => {
					let all_cov_keys = Object.keys(covariates_obj);
					let covariates_map = {};
					let format_year = Math.min(year, 2023);
					for (let i = 0; i < all_cov_keys.length; i++) {
						let local_key = all_cov_keys[i];
						let local_val = covariates_obj[local_key](format_year);
						covariates_map[local_key] = local_val;
					}
					
					return {
						covariates_map: covariates_map,
						model_obj: unified_model_path,
						options: {
							format: "float32"
						},
						output_file_path: `${this.intermediate_ols_rasters}ols_lfpr_${sex}_${year}.png`
					};
				}, {
					concurrency: options.concurrency,
					name: `LFPR OLS Raster Generation (${sex})`
				});
			}
		}
	}
	
	/**
	 * NORMALISE: Clamp OLS outputs into [0, 1] using a Tukey counterfactual.
	 * Valid in-range pixels pass through untouched; only pixels violating the
	 * [0, 1] bounds are replaced with their full Tukey-normalised counterfactual
	 * (log-tail C1-continuous regularisation + min-max stretch over the
	 * regularised range), which guarantees [0, 1] while preserving variance.
	 */
	static async C_normaliseOLSRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;

		//Declare local instance variables
		let landarea_raster = GeoPNG.loadNumberRasterImage(metadata_HYDE.input_raster_land_area, { format: "int32" });
		let sf = age_sex.sf();
		let years = landuse_HYDE.sorted_hyde_years;

		if (!fs.existsSync(this.intermediate_normalised_rasters)) fs.mkdirSync(this.intermediate_normalised_rasters, { recursive: true });
		
		for (let s = 0; s < this.sexes.length; s++) {
			let sex = this.sexes[s];
			
			await GeoPNG.processTimeseriesParallel({
				items: years,
				concurrency: options.concurrency || 4,
				name: `LFPR_OLS C_normaliseOLSRasters (${sex})`,
				handler: async (year) => {
					let popc_path = `${sf.input_popc_folder}stadester_population_${year}.png`;
					let ols_path = `${this.intermediate_ols_rasters}ols_lfpr_${sex}_${year}.png`;
					let normalised_path = `${this.intermediate_normalised_rasters}normalised_lfpr_${sex}_${year}.png`;
					
					if (!fs.existsSync(popc_path) || !fs.existsSync(ols_path)) return;
					if (!overwrite && fs.existsSync(normalised_path)) return;
					
					let popc_raster = GeoPNG.loadNumberRasterImage(popc_path, { format: "float32" });
					let ols_raster = GeoPNG.loadNumberRasterImage(ols_path, { format: "float32" });
					
					let valid_pixels = [];
					let sum = 0;
					for (let i = 0; i < ols_raster.data.length; i++) {
						if (landarea_raster.data[i] > 0 && popc_raster.data[i] > 0) {
							let local_value = ols_raster.data[i];
							if (!isNaN(local_value)) {
								valid_pixels.push(local_value);
								sum += local_value;
							}
						}
					}
					
					if (valid_pixels.length === 0) return;
					valid_pixels.sort((a, b) => a - b);
					
					let N = valid_pixels.length;
					let mean = sum / N;
					let sq_sum = 0;
					for (let i = 0; i < N; i++) sq_sum += Math.pow(valid_pixels[i] - mean, 2);
					let std = Math.sqrt(sq_sum / N);
					
					// Tukey's fences (per-year, from the actual OLS distribution)
					let q1 = valid_pixels[Math.floor(N * 0.25)];
					let q3 = valid_pixels[Math.floor(N * 0.75)];
					let iqr = q3 - q1;
					let alpha = (iqr > 1e-5) ? iqr : ((std > 1e-5) ? std : 0.01);
					
					let t_lower = q1 - (1.5 * alpha);
					let t_upper = q3 + (1.5 * alpha);
					
					let regularise = function (x) {
						if (x > t_upper) return t_upper + alpha * Math.log(1 + ((x - t_upper) / alpha));
						if (x < t_lower) return t_lower - alpha * Math.log(1 + ((t_lower - x) / alpha));
						return x;
					};
					
					// Full Tukey normalisation range (guaranteed to land within [0, 1])
					let reg_min = regularise(valid_pixels[0]);
					let reg_max = regularise(valid_pixels[N - 1]);
					let reg_range = reg_max - reg_min;
					
					let tukey_counterfactual = function (x) {
						let local_regularised = regularise(x);
						return (reg_range > 0) ? ((local_regularised - reg_min) / reg_range) : 0.5;
					};
					
					let normalised_map = new Float32Array(ols_raster.data.length);
					for (let i = 0; i < ols_raster.data.length; i++) {
						if (landarea_raster.data[i] > 0 && popc_raster.data[i] > 0) {
							let local_value = ols_raster.data[i];
							if (isNaN(local_value)) continue;
							
							if (local_value >= 0.0 && local_value <= 1.0) {
								// Valid pixel: pass through untouched
								normalised_map[i] = local_value;
							} else {
								// Invalid pixel: replace with the full Tukey counterfactual,
								// which is guaranteed to land in [0, 1] and preserves variance
								let counterfactual = tukey_counterfactual(local_value);
								normalised_map[i] = Math.max(0.0, Math.min(1.0, counterfactual));
							}
						}
					}
					
					GeoPNG.saveNumberRasterImage({
						file_path: normalised_path,
						format: "float32",
						width: ols_raster.width,
						height: ols_raster.height,
						function: (local_index) => normalised_map[local_index]
					});
					
					console.log(`- Normalised LFPR raster for ${sex}, year ${year}: ${normalised_path}`);
				}
			});
		}
	}
	
	/**
	 * CLAMP & GRAVITY BLUR: Combine known data (targets) and dissolve arbitrary colonial borders pre-1850.
	 */
	static async D_applyGravityAndClamp (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};

		//Declare local instance variables
		let geocode_raster = GeoPNG.loadImage(admin_modern.input_geocodes_raster);
		let items = [];
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
		let sf = age_sex.sf();
		let years = landuse_HYDE.sorted_hyde_years;

		if (!fs.existsSync(this.output_lfpr_rates)) fs.mkdirSync(this.output_lfpr_rates, { recursive: true });

		for (let s = 0; s < this.sexes.length; s++) {
			let sex = this.sexes[s];
			for (let y = 0; y < years.length; y++) {
				let year = years[y];
				let normalised_path = `${this.intermediate_normalised_rasters}normalised_lfpr_${sex}_${year}.png`;
				let output_path = `${this.output_lfpr_rates}lfpr_${sex}_${year}.png`;

				if (!fs.existsSync(normalised_path)) continue;
				if (!overwrite && fs.existsSync(output_path)) continue;

				items.push({ sex: sex, year: year });
			}
		}

		if (items.length === 0) return [];

		//Return statement
		return await GeoPNG.processTimeseriesParallel({
			concurrency: options.concurrency || 8,
			items: items,
			name: "LFPR D_applyGravityAndClamp",
			handler: async (item) => {
				let sex = item.sex;
				let year = item.year;
				let normalised_path = `${this.intermediate_normalised_rasters}normalised_lfpr_${sex}_${year}.png`;
				let target_path = `${LFPR_Olivetti.intermediate_rasters_folder}lfpr_${sex}_${year}.png`;
				let output_path = `${this.output_lfpr_rates}lfpr_${sex}_${year}.png`;

				let normalised_raster = GeoPNG.loadNumberRasterImage(normalised_path, { format: "float32" });
				let target_raster = fs.existsSync(target_path) ? GeoPNG.loadNumberRasterImage(target_path, { format: "float32" }) : null;

				let popc_path = `${sf.input_popc_folder}stadester_population_${year}.png`;
				let popc_raster = fs.existsSync(popc_path) ? GeoPNG.loadNumberRasterImage(popc_path, { format: "float32" }) : null;

				let processed_data = new Float32Array(normalised_raster.data.length);

				// 1. Initial Clamping (prioritise ground-truth Olivetti targets)
				for (let i = 0; i < processed_data.length; i++) {
					let t_val = target_raster ? target_raster.data[i] : 0;
					let n_val = normalised_raster.data[i];
					processed_data[i] = (t_val > 0 && !isNaN(t_val)) ? t_val : (isNaN(n_val) ? 0 : n_val);
				}

				// 2. Gravity Interpolation (Pre-1850) -> Prevent anachronistic sharp borders
				if (year < 1850 && popc_raster && geocode_raster) {
					try {
						processed_data = GeoPNG.dasymetricBlur({
							mask_data: geocode_raster.data,
							pop_data: popc_raster.data,
							target_data: processed_data,
							height: normalised_raster.height,
							width: normalised_raster.width,
							radius: 64
						});
					} catch (e) {
						console.error(`[ERROR] Gravity Blur failed for LFPR ${sex} year ${year}:`, e);
					}
				}

				GeoPNG.saveNumberRasterImage({
					file_path: output_path,
					format: "float32",
					width: normalised_raster.width,
					height: normalised_raster.height,
					function: (idx) => Math.max(0.0, Math.min(1.0, processed_data[idx]))
				});
			}
		});
	}
	
	/**
	 * DERIVE: Synthesise the Absolute Active Labourforce using LFPR rates * Local Demographics
	 */
	static async E_deriveActiveLabourforce (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};

		//Declare local instance variables
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
		let sexes = this.sexes;
		let working_cohorts = this.working_cohorts;
		let years = landuse_HYDE.sorted_hyde_years;

		if (!fs.existsSync(this.output_active_labourforce)) fs.mkdirSync(this.output_active_labourforce, { recursive: true });

		let target_years = years.filter((year) => {
			if (overwrite) return true;
			for (let s = 0; s < sexes.length; s++) {
				if (!fs.existsSync(`${this.output_active_labourforce}labourforce_${sexes[s]}_${year}.png`)) return true;
			}
			if (!fs.existsSync(`${this.output_active_labourforce}labourforce_t_${year}.png`)) return true;
			return false;
		});

		if (target_years.length === 0) return [];

		//Return statement
		return await GeoPNG.processTimeseriesParallel({
			concurrency: options.concurrency || 8,
			items: target_years,
			name: "LFPR E_deriveActiveLabourforce",
			handler: async (year) => {
				let active_counts = { f: null, m: null, total: null };
				let any_missing = false;

				for (let s = 0; s < sexes.length; s++) {
					let sex = sexes[s];
					let lfpr_path = `${this.output_lfpr_rates}lfpr_${sex}_${year}.png`;
					let output_count_path = `${this.output_active_labourforce}labourforce_${sex}_${year}.png`;

					if (!fs.existsSync(lfpr_path)) { any_missing = true; break; }

					let lfpr_raster = GeoPNG.loadNumberRasterImage(lfpr_path, { format: "float32" });
					let total_working_pop = new Float32Array(lfpr_raster.data.length);

					for (let c = 0; c < working_cohorts.length; c++) {
						let cohort = working_cohorts[c];
						let c_path = `${age_sex.output_rasters}${sex}_${cohort}_${year}.png`;

						if (fs.existsSync(c_path)) {
							let c_raster = GeoPNG.loadNumberRasterImage(c_path, { format: "float32" });
							for (let i = 0; i < c_raster.data.length; i++) {
								if (!isNaN(c_raster.data[i]) && c_raster.data[i] > 0) {
									total_working_pop[i] += c_raster.data[i];
								}
							}
						}
					}

					let count_array = new Float32Array(lfpr_raster.data.length);
					for (let i = 0; i < count_array.length; i++) {
						let rate = lfpr_raster.data[i];
						let pop = total_working_pop[i];
						if (rate > 0 && pop > 0 && !isNaN(rate)) {
							count_array[i] = rate * pop;
						}
					}

					active_counts[sex] = { array: count_array, height: lfpr_raster.height, width: lfpr_raster.width };

					if (overwrite || !fs.existsSync(output_count_path)) {
						GeoPNG.saveNumberRasterImage({
							file_path: output_count_path,
							format: "float32",
							height: active_counts[sex].height,
							width: active_counts[sex].width,
							function: (idx) => active_counts[sex].array[idx]
						});
					}
				}

				if (any_missing) return;

				let total_path = `${this.output_active_labourforce}labourforce_t_${year}.png`;
				if ((overwrite || !fs.existsSync(total_path)) && active_counts.f && active_counts.m) {
					GeoPNG.saveNumberRasterImage({
						file_path: total_path,
						format: "float32",
						height: active_counts.f.height,
						width: active_counts.f.width,
						function: (idx) => active_counts.f.array[idx] + active_counts.m.array[idx]
					});
				}
			}
		});
	}
	
	static async processRasters (arg0_options) {
		let options = (arg0_options) ? arg0_options : {};
		if (!options.exclude) options.exclude = [];
		if (options.skip_training || options.use_existing_models || options.train === false) {
			if (!options.exclude.includes("A")) options.exclude.push("A");
			console.log(`[LFPR_OLS] Skipping Step A training (using existing models).`);
		}
		
		if (!options.exclude.includes("A")) await this.A_trainOLSModels(options);
		if (!options.exclude.includes("B")) await this.B_generateOLSRasters(options);
		if (!options.exclude.includes("C")) await this.C_normaliseOLSRasters(options);
		if (!options.exclude.includes("D")) await this.D_applyGravityAndClamp(options);
		if (!options.exclude.includes("E")) await this.E_deriveActiveLabourforce(options);
	}
};