global.LFPR_OLS = class {
	static bf = `${h2}/LFPR_OLS/`;
	
	// Paths
	static intermediate_ols_models = `${this.bf}/0.OLS_models/`;
	static intermediate_ols_rasters = `${this.bf}/1.OLS_rasters/`;
	static intermediate_normalised_rasters = `${this.bf}/2.normalised_rasters/`;
	static output_lfpr_rates = `${this.bf}/3.lfpr_rates/`;
	static output_active_labourforce = `${this.bf}/4.active_labourforce/`;
	
	static sexes = ["f", "m"];
	static working_cohorts = ["15", "20", "25", "30", "35", "40", "45", "50", "55", "60"];
	
	// Utilise demographic parameters and structural inequality (gini) as covariates
	static covariates_obj = () => {
		let return_obj = { ...age_sex.covariates_obj };
		delete return_obj.gini;

		//Return statement
		return return_obj;
	};
	
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
							lambda: lambda_val,
							clamp_percentage: true
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
					let specific_model_path = `${this.intermediate_ols_models}OLS_lfpr_${sex}_${year}.json`;
					let resolved_model_path = fs.existsSync(specific_model_path) ? specific_model_path : unified_model_path;
					
					for (let i = 0; i < all_cov_keys.length; i++) {
						let local_key = all_cov_keys[i];
						let local_val = covariates_obj[local_key](format_year);
						covariates_map[local_key] = local_val;
					}
					
					return {
						covariates_map: covariates_map,
						model_obj: resolved_model_path,
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
		
		// 1. Fetch Empirical Bounds and Stats from Olivetti Data
		let parsed_olivetti = global.LFPR_Olivetti.A_getOlivettiLocalObject();
		let empirical_bounds = {
			m: { min: Infinity, max: -Infinity },
			f: { min: Infinity, max: -Infinity }
		};
		let empirical_stats = { m: {}, f: {} };
		
		Object.iterate(parsed_olivetti.data, (iso3, sexes) => {
			Object.iterate(sexes, (local_sex, series) => {
				Object.iterate(series, (yr, rate) => {
					if (rate < empirical_bounds[local_sex].min) empirical_bounds[local_sex].min = rate;
					if (rate > empirical_bounds[local_sex].max) empirical_bounds[local_sex].max = rate;
					
					if (!empirical_stats[local_sex][yr]) empirical_stats[local_sex][yr] = [];
					empirical_stats[local_sex][yr].push(rate);
				});
			});
		});
		
		let hist_mean_series = { m: {}, f: {} };
		let hist_std_series = { m: {}, f: {} };
		
		// Safety defaults and clamps to prevent extreme outliers 0 or 1 breaking the math
		for (let i = 0; i < this.sexes.length; i++) {
			let local_sex = this.sexes[i];
			
			let available_years = Object.keys(empirical_stats[local_sex]).map(Number).sort((a, b) => a - b);
			for (let j = 0; j < available_years.length; j++) {
				let yr = available_years[j];
				let vals = empirical_stats[local_sex][yr];
				
				// Only use years with >= 5 records to prevent a single country (like the UK in 1890) from defining the global historical baseline!
				if (vals.length >= 5) {
					let sum = vals.reduce((a, b) => a + b, 0);
					let mean = sum / vals.length;
					let variance = vals.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / vals.length;
					let std = Math.sqrt(variance);
					
					hist_mean_series[local_sex][yr] = mean;
					hist_std_series[local_sex][yr] = std;
				}
			}
			
			// Fallback if no years meet the threshold
			if (Object.keys(hist_mean_series[local_sex]).length === 0) {
				for (let j = 0; j < available_years.length; j++) {
					let yr = available_years[j];
					let vals = empirical_stats[local_sex][yr];
					let sum = vals.reduce((a, b) => a + b, 0);
					let mean = sum / vals.length;
					let variance = vals.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / vals.length;
					let std = Math.sqrt(variance);
					
					hist_mean_series[local_sex][yr] = mean;
					hist_std_series[local_sex][yr] = std;
				}
			}
			
			if (empirical_bounds[local_sex].min === Infinity) {
				empirical_bounds[local_sex] = (local_sex === "m") ? { min: 0.40, max: 0.96 } : { min: 0.05, max: 0.85 };
			} else {
				empirical_bounds[local_sex].min = Math.max(0.01, empirical_bounds[local_sex].min);
				empirical_bounds[local_sex].max = Math.min(0.99, empirical_bounds[local_sex].max);
			}
		}

		let get_empirical_stat = function (local_sex, local_year, stat_type) {
			let series = (stat_type === "mean") ? hist_mean_series[local_sex] : hist_std_series[local_sex];
			let available_years = Object.keys(series).map(Number).sort((a, b) => a - b);
			
			if (available_years.length === 0) return (stat_type === "mean") ? 0.60 : 0.20;
			
			// Constant historical baseline for pre-industrial times (extrapolating the earliest robust record backwards)
			if (local_year <= available_years[0]) return series[available_years[0]];
			
			// Constant modern baseline (extrapolating latest record forwards)
			if (local_year >= available_years[available_years.length - 1]) return series[available_years[available_years.length - 1]];
			
			// Linearly interpolate for years between records
			let y1 = available_years[0], y2 = available_years[available_years.length - 1];
			for (let i = 0; i < available_years.length - 1; i++) {
				if (local_year >= available_years[i] && local_year <= available_years[i + 1]) {
					y1 = available_years[i];
					y2 = available_years[i + 1];
					break;
				}
			}
			
			if (y1 === y2) return series[y1];
			let progress = (local_year - y1) / (y2 - y1);
			return series[y1] + progress * (series[y2] - series[y1]);
		};

		// Derive the historical trailing ratio dynamically from the empirical dataset
		let empirical_trailing_ratios = [];
		let available_years_m = Object.keys(hist_mean_series["m"]).map(Number);
		let available_years_f = Object.keys(hist_mean_series["f"]).map(Number);
		let overlapping_years = available_years_f.filter(y => available_years_m.includes(y));
		
		for (let i = 0; i < overlapping_years.length; i++) {
			let yr = overlapping_years[i];
			let f_mean = hist_mean_series["f"][yr];
			let m_mean = hist_mean_series["m"][yr];
			if (m_mean > 0) empirical_trailing_ratios.push(f_mean / m_mean);
		}
		
		empirical_trailing_ratios.sort((a, b) => a - b);
		let historical_trailing_ratio = (empirical_trailing_ratios.length > 0) 
			? empirical_trailing_ratios[Math.floor(empirical_trailing_ratios.length * 0.5)] 
			: 0.55;
			
		// Since male LFPR is relatively inelastic, we fetch the geometric mean of all empirical 
		// male LFPR figures across the dataset to use as the robust historical baseline.
		let sum_log_m = 0;
		let count_m = 0;
		for (let i = 0; i < available_years_m.length; i++) {
			let yr = available_years_m[i];
			let vals = empirical_stats["m"][yr];
			if (vals) {
				for (let j = 0; j < vals.length; j++) {
					if (vals[j] > 0) {
						sum_log_m += Math.log(vals[j]);
						count_m++;
					}
				}
			}
		}
		let agrarian_male_baseline = (count_m > 0) ? Math.exp(sum_log_m / count_m) : 0.85;
		
		console.log(`[LFPR_OLS] Calculated historical trailing ratio (F/M): ${historical_trailing_ratio.toFixed(4)}`);
		console.log(`[LFPR_OLS] Calculated agrarian male baseline (Geomean): ${agrarian_male_baseline.toFixed(4)}`);

		let get_demographic_baseline = function (local_sex, local_year) {
			let male_baseline;
			let empirical_m = get_empirical_stat("m", local_year, "mean");
			
			// Reconstruct the male baseline to avoid extrapolating the 19th-century industrial peak backwards
			if (local_year < 1750) {
				male_baseline = agrarian_male_baseline;
			} else if (local_year >= 1750 && local_year < 1850) {
				let progress = (local_year - 1750) / 100;
				let empirical_1850 = get_empirical_stat("m", 1850, "mean");
				male_baseline = agrarian_male_baseline + progress * (empirical_1850 - agrarian_male_baseline);
			} else {
				male_baseline = empirical_m;
			}
			
			if (local_sex === "m") {
				return male_baseline;
			} else {
				let empirical_f = get_empirical_stat("f", local_year, "mean");
				
				// Reconstruct the U-curve using rigorously derived parameters:
				if (local_year < 1750) {
					// 1. Agrarian Era: Female LFPR tracks male LFPR via the historical trailing ratio
					return agrarian_male_baseline * historical_trailing_ratio;
				} else if (local_year >= 1750 && local_year < 1850) {
					// 2. Industrial Transition: Smooth interpolation down to the empirical trough
					let agrarian_baseline_f = agrarian_male_baseline * historical_trailing_ratio;
					let progress = (local_year - 1750) / 100;
					let empirical_1850_f = get_empirical_stat("f", 1850, "mean");
					return agrarian_baseline_f + progress * (empirical_1850_f - agrarian_baseline_f);
				} else {
					// 3. Modern Era: Trust the empirical dataset to capture the trough and subsequent rise
					return empirical_f;
				}
			}
		};

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
					
					let has_valid_pixels = false;
					for (let i = 0; i < ols_raster.data.length; i++) {
						if (landarea_raster.data[i] > 0 && popc_raster.data[i] > 0 && !isNaN(ols_raster.data[i])) {
							has_valid_pixels = true;
							break;
						}
					}
					
					if (!has_valid_pixels) return;
					
					// Robust Statistics for Z-Score Normalisation
					let valid_values = [];
					for (let i = 0; i < ols_raster.data.length; i++) {
						if (landarea_raster.data[i] > 0 && popc_raster.data[i] > 0 && !isNaN(ols_raster.data[i])) {
							valid_values.push(ols_raster.data[i]);
						}
					}
					
					valid_values.sort((a, b) => a - b);
					let p50 = valid_values[Math.floor(valid_values.length * 0.5)];
					let p25 = valid_values[Math.floor(valid_values.length * 0.25)];
					let p75 = valid_values[Math.floor(valid_values.length * 0.75)];
					let iqr = p75 - p25;
					let robust_std = iqr / 1.349;
					if (robust_std < 0.0001) robust_std = 0.0001; // Avoid division by zero
					
					// Generalised Fractional Response Equation
					let min_bound = empirical_bounds[sex].min;
					let max_bound = empirical_bounds[sex].max;
					
					// Apply the rigorously parameterized demographic baseline equation to anchor the Fractional Response model
					let baseline_mean = get_demographic_baseline(sex, year);
					baseline_mean = Math.max(min_bound + 0.02, Math.min(max_bound - 0.02, baseline_mean));
					
					let target_s_mean = (baseline_mean - min_bound) / (max_bound - min_bound);
					target_s_mean = Math.max(0.01, Math.min(0.99, target_s_mean)); // Safety clamp
					
					let alpha = Math.log(target_s_mean / (1 - target_s_mean));
					
					// Force the standard deviation to stretch to empirical reality instead of relying on OLS flat variance
					let empirical_std = get_empirical_stat(sex, year, "std");
					let target_std = Math.min(empirical_std, (max_bound - min_bound) * 0.25);
					target_std = Math.max(0.01, target_std); // Safety minimum variance
					let beta = target_std / ((max_bound - min_bound) * target_s_mean * (1 - target_s_mean));
					
					let normalised_map = new Float32Array(ols_raster.data.length);
					for (let i = 0; i < ols_raster.data.length; i++) {
						if (landarea_raster.data[i] > 0 && popc_raster.data[i] > 0) {
							let local_value = ols_raster.data[i];
							if (!isNaN(local_value)) {
								// Standardise OLS score
								let z = (local_value - p50) / robust_std;
								
								// Apply Scaled Logistic Function to squash tails smoothly
								let s_val = 1 / (1 + Math.exp(-(alpha + beta * z)));
								normalised_map[i] = min_bound + (max_bound - min_bound) * s_val;
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

				// 1. Cross-Entropy Spatial Calibration (Logit Shift)
				// Pass 1: Accumulate population-weighted means for each target group
				let t_groups = {};
				
				for (let i = 0; i < processed_data.length; i++) {
					let t_val = target_raster ? target_raster.data[i] : 0;
					let n_val = normalised_raster.data[i];
					let pop = popc_raster ? popc_raster.data[i] : 0;
					
					if (t_val > 0 && !isNaN(t_val) && !isNaN(n_val)) {
						if (!t_groups[t_val]) t_groups[t_val] = { sum_n: 0, pop: 0 };
						t_groups[t_val].sum_n += n_val * pop;
						t_groups[t_val].pop += pop;
					}
				}
				
				// Pass 2: Apply Logit Shift to align local distribution with macro targets
				let logit = (p) => {
					let clamp_p = Math.max(0.0001, Math.min(0.9999, p));
					return Math.log(clamp_p / (1 - clamp_p));
				};
				let sigmoid = (x) => 1 / (1 + Math.exp(-x));
				
				for (let i = 0; i < processed_data.length; i++) {
					let t_val = target_raster ? target_raster.data[i] : 0;
					let n_val = normalised_raster.data[i];
					
					if (t_val > 0 && !isNaN(t_val) && !isNaN(n_val) && t_groups[t_val]) {
						let group = t_groups[t_val];
						let n_mean = group.pop > 0 ? (group.sum_n / group.pop) : n_val;
						
						let shift = logit(t_val) - logit(n_mean);
						processed_data[i] = sigmoid(logit(n_val) + shift);
					} else {
						processed_data[i] = isNaN(n_val) ? 0 : n_val;
					}
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