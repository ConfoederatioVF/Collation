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
		let options = (arg0_options) ? arg0_options : {};
		if (!options.lambda) options.lambda = 1;
		
		if (!fs.existsSync(this.intermediate_ols_models)) fs.mkdirSync(this.intermediate_ols_models, { recursive: true });
		
		let years = landuse_HYDE.sorted_hyde_years;
		let covariates_obj = this.covariates_obj();
		
		for (let s = 0; s < this.sexes.length; s++) {
			let sex = this.sexes[s];
			
			for (let y = 0; y < years.length; y++) {
				let year = years[y];
				let target_path = `${LFPR_Olivetti.intermediate_rasters_folder}lfpr_${sex}_${year}.png`;
				let model_path = `${this.intermediate_ols_models}OLS_lfpr_${sex}_${year}.json`;
				
				if (!fs.existsSync(target_path)) continue;
				if (fs.existsSync(model_path)) continue;
				
				let format_year = Math.min(year, 2023);
				let loaded_obj = await Statistics.loadOLSCovariates(target_path, {
					utility_format: "float32",
					covariates_obj: covariates_obj,
					formatting_parameters: [format_year]
				});
				
				if (!loaded_obj.X || loaded_obj.X.length === 0) continue;
				
				await Statistics.trainOLSModel(model_path, loaded_obj, {
					...options,
					lambda: options.lambda,
					key: year.toString()
				});
				
				console.log(`- Trained LFPR OLS model for Sex: ${sex}, Year: ${year} (${loaded_obj.X.length} samples)`);
				await Blacktraffic.yield();
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
	
	/**
	 * GENERATE: Broadcast the Geomeaned OLS models over the covariate stack for all years.
	 */
	static async B_generateOLSRasters () {
		if (!fs.existsSync(this.intermediate_ols_rasters)) fs.mkdirSync(this.intermediate_ols_rasters, { recursive: true });
		
		let years = landuse_HYDE.sorted_hyde_years;
		let covariates_obj = this.covariates_obj();
		
		for (let s = 0; s < this.sexes.length; s++) {
			let sex = this.sexes[s];
			let unified_model_path = `${this.intermediate_ols_models}geomean_OLS_lfpr_${sex}.json`;
			
			for (let y = 0; y < years.length; y++) {
				let year = years[y];
				let output_path = `${this.intermediate_ols_rasters}ols_lfpr_${sex}_${year}.png`;
				
				if (fs.existsSync(output_path)) continue;
				
				let model_path = `${this.intermediate_ols_models}OLS_lfpr_${sex}_${year}.json`;
				if (!fs.existsSync(model_path)) model_path = unified_model_path;
				
				if (!fs.existsSync(model_path)) continue;
				
				let format_year = Math.min(year, 2023);
				console.log(`Generating LFPR OLS raster for ${sex} year ${year}`);
				
				await Statistics.generateOLSRaster(output_path, {
					covariates_obj: covariates_obj,
					format: "float32",
					formatting_parameters: [format_year],
					model_obj: model_path
				});
				
				await Blacktraffic.yield();
			}
		}
	}
	
	/**
	 * NORMALISE: Log-tail C1-continuous regularisation to squash OLS outputs into a [0, 1] range.
	 */
	static async C_normaliseOLSRasters () {
		if (!fs.existsSync(this.intermediate_normalised_rasters)) fs.mkdirSync(this.intermediate_normalised_rasters, { recursive: true });
		
		let years = landuse_HYDE.sorted_hyde_years;
		let sf = age_sex.sf();
		let landarea_raster = GeoPNG.loadNumberRasterImage(metadata_HYDE.input_raster_land_area, { format: "int32" });
		
		for (let s = 0; s < this.sexes.length; s++) {
			let sex = this.sexes[s];
			
			for (let y = 0; y < years.length; y++) {
				let year = years[y];
				
				let popc_path = `${sf.input_popc_folder}stadester_population_${year}.png`;
				let ols_path = `${this.intermediate_ols_rasters}ols_lfpr_${sex}_${year}.png`;
				let normalised_path = `${this.intermediate_normalised_rasters}normalised_lfpr_${sex}_${year}.png`;
				
				if (!fs.existsSync(popc_path) || !fs.existsSync(ols_path)) continue;
				if (fs.existsSync(normalised_path)) continue;
				
				let popc_raster = GeoPNG.loadNumberRasterImage(popc_path, { format: "int32" });
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
				
				if (valid_pixels.length === 0) continue;
				valid_pixels.sort((a, b) => a - b);
				
				let N = valid_pixels.length;
				let mean = sum / N;
				let sq_sum = 0;
				for (let i = 0; i < N; i++) sq_sum += Math.pow(valid_pixels[i] - mean, 2);
				let std = Math.sqrt(sq_sum / N);
				
				// Tukey's fences
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
				
				let reg_min = regularise(valid_pixels[0]);
				let reg_max = regularise(valid_pixels[N - 1]);
				let reg_range = reg_max - reg_min;
				
				let normalised_map = new Float32Array(ols_raster.data.length);
				for (let i = 0; i < ols_raster.data.length; i++) {
					if (landarea_raster.data[i] > 0 && popc_raster.data[i] > 0) {
						let local_value = ols_raster.data[i];
						if (isNaN(local_value)) continue;
						
						let local_regularised = regularise(local_value);
						let unit_value = (reg_range > 0) ? ((local_regularised - reg_min) / reg_range) : 0.5;
						
						// Hard bounds to strictly conform to [0, 1] LFPR rates
						normalised_map[i] = Math.max(0.0, Math.min(1.0, unit_value));
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
				await Blacktraffic.yield();
			}
		}
	}
	
	/**
	 * CLAMP & GRAVITY BLUR: Combine known data (targets) and dissolve arbitrary colonial borders pre-1850.
	 */
	static async D_applyGravityAndClamp () {
		if (!fs.existsSync(this.output_lfpr_rates)) fs.mkdirSync(this.output_lfpr_rates, { recursive: true });
		
		let years = landuse_HYDE.sorted_hyde_years;
		let sf = age_sex.sf();
		let geocode_raster = GeoPNG.loadImage(admin_modern.input_geocodes_raster);
		
		for (let s = 0; s < this.sexes.length; s++) {
			let sex = this.sexes[s];
			
			for (let y = 0; y < years.length; y++) {
				let year = years[y];
				let normalised_path = `${this.intermediate_normalised_rasters}normalised_lfpr_${sex}_${year}.png`;
				let target_path = `${LFPR_Olivetti.intermediate_rasters_folder}lfpr_${sex}_${year}.png`;
				let output_path = `${this.output_lfpr_rates}lfpr_${sex}_${year}.png`;
				
				if (!fs.existsSync(normalised_path)) continue;
				if (fs.existsSync(output_path)) continue;
				
				let normalised_raster = GeoPNG.loadNumberRasterImage(normalised_path, { format: "float32" });
				let target_raster = fs.existsSync(target_path) ? GeoPNG.loadNumberRasterImage(target_path, { format: "float32" }) : null;
				
				let popc_path = `${sf.input_popc_folder}stadester_population_${year}.png`;
				let popc_raster = fs.existsSync(popc_path) ? GeoPNG.loadNumberRasterImage(popc_path, { format: "int32" }) : null;
				
				let processed_data = new Float32Array(normalised_raster.data.length);
				
				// 1. Initial Clamping (prioritise ground-truth Olivetti targets)
				for (let i = 0; i < processed_data.length; i++) {
					let t_val = target_raster ? target_raster.data[i] : 0;
					let n_val = normalised_raster.data[i];
					processed_data[i] = (t_val > 0 && !isNaN(t_val)) ? t_val : (isNaN(n_val) ? 0 : n_val);
				}
				
				// 2. Gravity Interpolation (Pre-1850) -> Prevent anachronistic sharp borders
				if (year < 1850 && popc_raster && geocode_raster) {
					console.log(`- Applying Dasymetric Gravity Blur for ${sex}, year ${year} ...`);
					try {
						processed_data = GeoPNG.dasymetricBlur({
							mask_data: geocode_raster.data,
							pop_data: popc_raster.data,
							target_data: processed_data,
							height: normalised_raster.height,
							width: normalised_raster.width,
							radius: 64 // Wide gravitational radius
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
				
				console.log(`- Saved final LFPR Rate map: ${output_path}`);
				await Blacktraffic.yield();
			}
		}
	}
	
	/**
	 * DERIVE: Synthesise the Absolute Active Labourforce using LFPR rates * Local Demographics
	 */
	static async E_deriveActiveLabourforce () {
		if (!fs.existsSync(this.output_active_labourforce)) fs.mkdirSync(this.output_active_labourforce, { recursive: true });
		
		let years = landuse_HYDE.sorted_hyde_years;
		
		for (let y = 0; y < years.length; y++) {
			let year = years[y];
			let any_missing = false;
			let active_counts = { f: null, m: null, total: null };
			
			for (let s = 0; s < this.sexes.length; s++) {
				let sex = this.sexes[s];
				let lfpr_path = `${this.output_lfpr_rates}lfpr_${sex}_${year}.png`;
				let output_count_path = `${this.output_active_labourforce}active_labourforce_${sex}_${year}.png`;
				
				if (!fs.existsSync(lfpr_path)) { any_missing = true; break; }
				
				let lfpr_raster = GeoPNG.loadNumberRasterImage(lfpr_path, { format: "float32" });
				let total_working_pop = new Float32Array(lfpr_raster.data.length);
				
				// Aggregate all working-age cohorts (15+) for the current sex and year
				for (let c = 0; c < this.working_cohorts.length; c++) {
					let cohort = this.working_cohorts[c];
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
				
				// Create the absolute count raster for this sex
				let count_array = new Float32Array(lfpr_raster.data.length);
				for (let i = 0; i < count_array.length; i++) {
					let rate = lfpr_raster.data[i];
					let pop = total_working_pop[i];
					if (rate > 0 && pop > 0 && !isNaN(rate)) {
						count_array[i] = rate * pop;
					}
				}
				
				active_counts[sex] = { array: count_array, width: lfpr_raster.width, height: lfpr_raster.height };
				
				if (!fs.existsSync(output_count_path)) {
					GeoPNG.saveNumberRasterImage({
						file_path: output_count_path,
						format: "float32",
						width: active_counts[sex].width,
						height: active_counts[sex].height,
						function: (idx) => active_counts[sex].array[idx]
					});
					console.log(`- Derived absolute active labourforce map for ${sex}, year ${year}`);
				}
			}
			
			if (any_missing) continue;
			
			// Compute total aggregate labourforce (Female + Male)
			let total_path = `${this.output_active_labourforce}active_labourforce_total_${year}.png`;
			if (!fs.existsSync(total_path) && active_counts.f && active_counts.m) {
				GeoPNG.saveNumberRasterImage({
					file_path: total_path,
					format: "float32",
					width: active_counts.f.width,
					height: active_counts.f.height,
					function: (idx) => active_counts.f.array[idx] + active_counts.m.array[idx]
				});
				console.log(`- Derived Total (Aggregate) active labourforce map for year ${year}`);
			}
			
			await Blacktraffic.yield();
		}
	}
	
	static async processRasters (arg0_options) {
		let options = (arg0_options) ? arg0_options : {};
		if (!options.exclude) options.exclude = [];
		
		if (!options.exclude.includes("A")) await this.A_trainOLSModels(options);
		if (!options.exclude.includes("B")) await this.B_generateOLSRasters();
		if (!options.exclude.includes("C")) await this.C_normaliseOLSRasters();
		if (!options.exclude.includes("D")) await this.D_applyGravityAndClamp();
		if (!options.exclude.includes("E")) await this.E_deriveActiveLabourforce();
	}
};