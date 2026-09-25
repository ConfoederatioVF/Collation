global.births_deaths_OLS = class {
	static bf = `${h2}/births_deaths_OLS/`;
	static covariates_obj = () => ({
		...age_sex.covariates_obj,
		"gini": (y) => [`${gini_Eoscala.output_rasters}gini_${y}.png`, "float32"]
	});
	static intermediate_birth_targets = `${this.bf}/0.birth_targets/`;
	static intermediate_female_death_targets = `${this.bf}/0.female_death_targets/`;
	static intermediate_male_death_targets = `${this.bf}/0.male_death_targets/`;
	static intermediate_ols_births = `${this.bf}/1.OLS_births/`;
	static intermediate_ols_female_deaths = `${this.bf}/1.OLS_female_deaths/`;
	static intermediate_ols_male_deaths = `${this.bf}/1.OLS_male_deaths/`;
	static intermediate_normalised_births = `${this.bf}/2.normalised_births/`;
	static intermediate_normalised_female_deaths = `${this.bf}/2.normalised_female_deaths/`;
	static intermediate_normalised_male_deaths = `${this.bf}/2.normalised_male_deaths/`;
	static intermediate_bounds = `${this.bf}/2.bounds/`;
	static output_births_folder = `${this.bf}/3.crude_births/`;
	static output_female_deaths_folder = `${this.bf}/3.female_crude_deaths/`;
	static output_male_deaths_folder = `${this.bf}/3.male_crude_deaths/`;
	static output_female_migration_folder = `${this.bf}/4.female_net_migration/`;
	static output_male_migration_folder = `${this.bf}/4.male_net_migration/`;
	static output_net_migration_folder = `${this.bf}/4.net_migration/`;
	
	/**
	 * Maps variable keys to their file/folder metadata across all pipeline stages.
	 * denominator: "cohort_00" (fraction of 0-1yo's attributable to births) or
	 * "cohort_decline" (fraction of successive-cohort declines attributable to deaths).
	 */
	static _getVariablesObj () {
		return {
			births: {
				denominator: "cohort_00",
				fraction_cap: 1.5,
				actual_folder_unwpp: births_deaths_UNWPP.output_crude_births_folder,
				actual_folder_hmd: births_deaths_HMD.output_crude_births_folder,
				actual_prefix: "births",
				target_folder: this.intermediate_birth_targets,
				ols_folder: this.intermediate_ols_births,
				normalised_folder: this.intermediate_normalised_births,
				output_folder: this.output_births_folder,
				model_prefix: "OLS_births_"
			},
			female_deaths: {
				denominator: "cohort_decline",
				fraction_cap: 3.0,
				sex: "f",
				actual_folder_unwpp: births_deaths_UNWPP.output_female_crude_deaths_folder,
				actual_folder_hmd: births_deaths_HMD.output_female_crude_deaths_folder,
				actual_prefix: "female_deaths",
				target_folder: this.intermediate_female_death_targets,
				ols_folder: this.intermediate_ols_female_deaths,
				normalised_folder: this.intermediate_normalised_female_deaths,
				output_folder: this.output_female_deaths_folder,
				model_prefix: "OLS_female_deaths_"
			},
			male_deaths: {
				denominator: "cohort_decline",
				fraction_cap: 3.0,
				sex: "m",
				actual_folder_unwpp: births_deaths_UNWPP.output_male_crude_deaths_folder,
				actual_folder_hmd: births_deaths_HMD.output_male_crude_deaths_folder,
				actual_prefix: "male_deaths",
				target_folder: this.intermediate_male_death_targets,
				ols_folder: this.intermediate_ols_male_deaths,
				normalised_folder: this.intermediate_normalised_male_deaths,
				output_folder: this.output_male_deaths_folder,
				model_prefix: "OLS_male_deaths_"
			}
		};
	}
	
	/**
	 * Returns the actual (HMD/UNWPP) count raster path for a variable/year, or null.
	 */
	static _getActualPath (arg0_variable_obj, arg1_year) {
		//Convert from parameters
		let variable_obj = arg0_variable_obj;
		let year = arg1_year;
		
		//Declare local instance variables
		let folder = (year >= 1950) ? variable_obj.actual_folder_unwpp : variable_obj.actual_folder_hmd;
		let local_path = `${folder}${variable_obj.actual_prefix}_${year}.png`;
		
		//Return statement
		return (fs.existsSync(local_path)) ? local_path : null;
	}
	
	/**
	 * Loads the local 0-1yo cohort population (f_00 + m_00) from the age_sex composite
	 * timeseries for a given year. This is the denominator for birth fractions.
	 */
	static _getCohort00Array (arg0_year) {
		//Convert from parameters
		let year = arg0_year;
		
		//Declare local instance variables
		let f_00_path = `${age_sex.output_rasters}f_00_${year}.png`;
		let m_00_path = `${age_sex.output_rasters}m_00_${year}.png`;
		
		if (!fs.existsSync(f_00_path) || !fs.existsSync(m_00_path)) return null;
		
		let f_00_raster = GeoPNG.loadNumberRasterImage(f_00_path, { format: "float32" });
		let m_00_raster = GeoPNG.loadNumberRasterImage(m_00_path, { format: "float32" });
		
		let return_array = new Float32Array(f_00_raster.data.length);
		for (let i = 0; i < return_array.length; i++) {
			let local_f = (isNaN(f_00_raster.data[i])) ? 0 : f_00_raster.data[i];
			let local_m = (isNaN(m_00_raster.data[i])) ? 0 : m_00_raster.data[i];
			return_array[i] = local_f + local_m;
		}
		
		return return_array;
	}
	
	/**
	 * Computes the statistically robust intrinsic mortality (Crude Deaths) for the population pyramid.
	 * 1. Annualises all cohorts based on their specific band widths.
	 * 2. Uses Lotka's Equation to deflate the population growth rate (r).
	 * 3. Applies Isotonic Regression (PAVA) to statistically fit a monotonically decreasing survival curve,
	 *    which perfectly eliminates migration bulges while preserving infant/elderly mortality spikes.
	 *    Requires 0 magic numbers and 0 parametric assumptions.
	 */
	static _getCohortDeclineArray (arg0_sex, arg1_year) {
		let sex = arg0_sex;
		let year = arg1_year;
		
		let all_cohorts = age_sex.getCohorts();
		let sex_cohorts = all_cohorts.filter(c => c.startsWith(`${sex}_`));
		
		// Pure structural mapping of varying demographic band widths and midpoint ages
		let band_widths = new Float32Array(sex_cohorts.length);
		let midpoints = new Float32Array(sex_cohorts.length);
		let current_age = 0;
		for (let c = 0; c < sex_cohorts.length; c++) {
			let w = sex_cohorts[c].endsWith("_00") ? 1 : (sex_cohorts[c].endsWith("_01") ? 4 : 5);
			band_widths[c] = w;
			midpoints[c] = current_age + (w / 2);
			current_age += w;
		}
		
		let rasters = sex_cohorts.map(c => {
			let p = `${age_sex.output_rasters}${c}_${year}.png`;
			return fs.existsSync(p) ? GeoPNG.loadNumberRasterImage(p, { format: "float32" }) : null;
		});
		if (rasters.includes(null)) return null;
		
		let years = landuse_HYDE.sorted_hyde_years;
		let prev_year = years[Math.max(0, years.indexOf(year) - 1)];
		let year_gap = (year === prev_year) ? 1 : (year - prev_year);
		
		let sf = age_sex.sf();
		let popc_path = `${sf.input_popc_folder}stadester_population_${year}.png`;
		let prev_popc_path = `${sf.input_popc_folder}stadester_population_${prev_year}.png`;
		
		let pop_r = fs.existsSync(popc_path) ? GeoPNG.loadNumberRasterImage(popc_path, { format: "float32" }) : null;
		let prev_pop_r = fs.existsSync(prev_popc_path) ? GeoPNG.loadNumberRasterImage(prev_popc_path, { format: "float32" }) : null;
		
		let decline_array = new Float32Array(rasters[0].data.length);
		let cohort_count = rasters.length;
		
		// Pre-allocated flat arrays for Isotonic Regression (avoids millions of object GC pauses)
		let S = new Float32Array(cohort_count);
		let block_vals = new Float32Array(cohort_count);
		let block_weights = new Float32Array(cohort_count);
		let block_counts = new Int32Array(cohort_count);
		let S_monotonic = new Float32Array(cohort_count);
		
		for (let i = 0; i < decline_array.length; i++) {
			let local_pop = pop_r ? pop_r.data[i] : 0;
			if (local_pop <= 0) continue;
			
			// Compute exact local annualized growth rate (r)
			let prev_pop = prev_pop_r ? prev_pop_r.data[i] : local_pop;
			let r = (prev_pop > 0) ? Math.log(local_pop / prev_pop) / year_gap : 0;
			
			// 1. Construct the Lotka-adjusted stationary survival curve (S)
			for (let c = 0; c < cohort_count; c++) {
				let raw_val = rasters[c].data[i];
				let A = (isNaN(raw_val) || raw_val < 0 ? 0 : raw_val) / band_widths[c];
				S[c] = A * Math.exp(r * midpoints[c]);
			}
			
			// 2. Isotonic Regression (PAVA) - Enforce strictly monotonically decreasing survival curve
			let num_blocks = cohort_count;
			for (let c = 0; c < cohort_count; c++) {
				block_vals[c] = S[c];
				block_weights[c] = band_widths[c];
				block_counts[c] = 1;
			}
			
			let b = 0;
			while (b < num_blocks - 1) {
				// If a cohort is larger than the younger cohort, it is a migration bulge (violation)
				if (block_vals[b] < block_vals[b + 1]) {
					// Pool the adjacent violators into a flat plateau
					let w_sum = block_weights[b] + block_weights[b + 1];
					block_vals[b] = ((block_vals[b] * block_weights[b]) + (block_vals[b + 1] * block_weights[b + 1])) / w_sum;
					block_weights[b] = w_sum;
					block_counts[b] += block_counts[b + 1];
					
					// Shift remaining blocks left
					for (let k = b + 1; k < num_blocks - 1; k++) {
						block_vals[k] = block_vals[k + 1];
						block_weights[k] = block_weights[k + 1];
						block_counts[k] = block_counts[k + 1];
					}
					num_blocks--;
					if (b > 0) b--; // Step back to ensure the new pooled block doesn't violate its predecessor
				} else {
					b++;
				}
			}
			
			// Unpack the monotonically decreasing blocks back into the survival curve
			let idx = 0;
			for (let k = 0; k < num_blocks; k++) {
				for (let j = 0; j < block_counts[k]; j++) {
					S_monotonic[idx++] = block_vals[k];
				}
			}
			
			// 3. Extract exact intrinsic deaths using cohort-specific hazards
			let sum_deaths = 0;
			
			for (let c = 0; c < cohort_count - 1; c++) {
				let S_c = S_monotonic[c];
				let S_next = S_monotonic[c + 1];
				
				if (S_c > 0) {
					// Hazard rate \mu = (relative drop) / (age gap)
					let dx = midpoints[c + 1] - midpoints[c];
					let mu_c = (S_c - S_next) / (S_c * dx);
					
					let raw_val = rasters[c].data[i];
					if (!isNaN(raw_val) && raw_val > 0) sum_deaths += raw_val * mu_c;
				}
			}
			
			// Terminal cohort assumes bounded life expectancy equal to its band width
			let S_last = S_monotonic[cohort_count - 1];
			if (S_last > 0) {
				let mu_last = 1.0 / band_widths[cohort_count - 1];
				let raw_val = rasters[cohort_count - 1].data[i];
				if (!isNaN(raw_val) && raw_val > 0) sum_deaths += raw_val * mu_last;
			}
			
			decline_array[i] = sum_deaths;
		}
		
		return decline_array;
	}
	
	/**
	 * Resolves the denominator array for a variable/year.
	 */
	static _getDenominatorArray (arg0_variable_obj, arg1_year) {
		let variable_obj = arg0_variable_obj;
		let year = arg1_year;
		
		if (variable_obj.denominator === "cohort_00") return this._getCohort00Array(year);
		return this._getCohortDeclineArray(variable_obj.sex, year);
	}
	
	static async A_generateTargetRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;

		let variables_obj = this._getVariablesObj();
		let years = landuse_HYDE.sorted_hyde_years;
		if (options.years) years = years.filter(y => options.years.includes(y));
		
		await GeoPNG.processTimeseriesParallel({
			items: years,
			concurrency: options.concurrency || 4,
			name: "births_deaths_OLS A_generateTargetRasters",
			handler: async (year) => {
				let variable_keys = Object.keys(variables_obj);
				for (let v = 0; v < variable_keys.length; v++) {
					let variable_obj = variables_obj[variable_keys[v]];
					let target_path = `${variable_obj.target_folder}${variable_obj.actual_prefix}_target_${year}.png`;
					
					if (!overwrite && fs.existsSync(target_path)) continue;
					
					let actual_path = this._getActualPath(variable_obj, year);
					if (!actual_path) continue;
					
					let denominator_array = this._getDenominatorArray(variable_obj, year);
					if (!denominator_array) {
						console.warn(`- Missing composite cohort denominators for ${variable_obj.actual_prefix} year ${year}. Skipping target.`);
						continue;
					}
					
					let actual_raster = GeoPNG.loadNumberRasterImage(actual_path, { format: "float32" });
					let popc_path = `${age_sex.sf().input_popc_folder}stadester_population_${year}.png`;
					let popc_raster = fs.existsSync(popc_path) ? GeoPNG.loadNumberRasterImage(popc_path, { format: "float32" }) : null;
					
					GeoPNG.saveNumberRasterImage({
						file_path: target_path,
						format: "float32",
						width: actual_raster.width,
						height: actual_raster.height,
						function: (local_index) => {
							if (popc_raster && popc_raster.data[local_index] < 10000) return NaN;
							
							let local_count = actual_raster.data[local_index];
							if (isNaN(local_count) || local_count <= 0) return NaN;
							
							let local_denominator = denominator_array[local_index];
							if (local_denominator < 1) return NaN;
							
							return Math.min(variable_obj.fraction_cap, local_count / local_denominator);
						}
					});
					
					console.log(`- Generated target fraction raster: ${target_path}`);
				}
			}
		});
	}
	
	static async B_trainOLSModels (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		let lambda_val = (options.lambda !== undefined) ? options.lambda : 1;
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
		
		//Declare local instance variables
		let covariates_obj = this.covariates_obj();
		let variables_obj = this._getVariablesObj();
		let variable_keys = Object.keys(variables_obj);
		let years = landuse_HYDE.sorted_hyde_years;
		if (options.years) years = years.filter(y => options.years.includes(y));
		
		for (let v = 0; v < variable_keys.length; v++) {
			let variable_obj = variables_obj[variable_keys[v]];
			let target_years = years.filter((year) => {
				let target_path = `${variable_obj.target_folder}${variable_obj.actual_prefix}_target_${year}.png`;
				let model_path = `${variable_obj.ols_folder}${variable_obj.model_prefix}${year}.json`;
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
						output_file_path: `${variable_obj.ols_folder}${variable_obj.model_prefix}${year}.json`,
						target_file_path: `${variable_obj.target_folder}${variable_obj.actual_prefix}_target_${year}.png`,
						target_format: "float32"
					};
				}, {
					concurrency: options.concurrency,
					name: `OLS Training (${variable_obj.actual_prefix})`
				});
			}
			
			try {
				await Statistics.geomeanOLSModels(variable_obj.ols_folder, variable_obj.model_prefix, {
					weighting_function: (value) => Math.abs(value)
				});
			} catch (e) {
				console.error(`Error calculating geomean for ${variable_obj.actual_prefix} models:`, e);
			}
		}
	}
	
	static async C_generateOLSRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
		
		//Declare local instance variables
		let covariates_obj = this.covariates_obj();
		let variables_obj = this._getVariablesObj();
		let variable_keys = Object.keys(variables_obj);
		let years = landuse_HYDE.sorted_hyde_years;
		if (options.years) years = years.filter(y => options.years.includes(y));
		
		for (let v = 0; v < variable_keys.length; v++) {
			let variable_obj = variables_obj[variable_keys[v]];
			let unified_model_path = `${variable_obj.ols_folder}geomean_${variable_obj.model_prefix.replace(/_$/, "")}.json`;
			
			let target_years = years.filter((year) => {
				let output_path = `${variable_obj.ols_folder}ols_${variable_obj.actual_prefix}_${year}.png`;
				if (!overwrite && fs.existsSync(output_path)) return false;
				let model_path = `${variable_obj.ols_folder}${variable_obj.model_prefix}${year}.json`;
				if (!fs.existsSync(model_path)) model_path = unified_model_path;
				return fs.existsSync(model_path);
			});
			
			if (target_years.length > 0) {
				await Statistics.generateOLSRastersParallel(target_years, (year) => {
					let all_cov_keys = Object.keys(covariates_obj);
					let covariates_map = {};
					let format_year = Math.min(year, 2023);
					let model_path = `${variable_obj.ols_folder}${variable_obj.model_prefix}${year}.json`;
					if (!fs.existsSync(model_path)) model_path = unified_model_path;
					
					for (let i = 0; i < all_cov_keys.length; i++) {
						let local_key = all_cov_keys[i];
						let local_val = covariates_obj[local_key](format_year);
						covariates_map[local_key] = local_val;
					}
					
					return {
						covariates_map: covariates_map,
						model_obj: model_path,
						options: {
							format: "float32"
						},
						output_file_path: `${variable_obj.ols_folder}ols_${variable_obj.actual_prefix}_${year}.png`
					};
				}, {
					concurrency: options.concurrency,
					name: `OLS Raster Generation (${variable_obj.actual_prefix})`
				});
			}
		}
	}
	
	static async D_normaliseOLSRasters (arg0_options) {
		let options = (arg0_options) ? arg0_options : {};
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;

		let variables_obj = this._getVariablesObj();
		let years = landuse_HYDE.sorted_hyde_years;
		if (options.years) years = years.filter(y => options.years.includes(y));
		let sf = age_sex.sf();
		let landarea_raster = GeoPNG.loadNumberRasterImage(metadata_HYDE.input_raster_land_area, { format: "int32" });
		
		let variable_keys = Object.keys(variables_obj);
		for (let v = 0; v < variable_keys.length; v++) {
			let variable_obj = variables_obj[variable_keys[v]];
			
			let global_min = Infinity;
			let global_max = -Infinity;
			let yearly_target_stats = {};
			
			for (let y = 0; y < years.length; y++) {
				let year = years[y];
				let target_path = `${variable_obj.target_folder}${variable_obj.actual_prefix}_target_${year}.png`;
				
				if (!fs.existsSync(target_path)) continue;
				
				let target_raster = GeoPNG.loadNumberRasterImage(target_path, { format: "float32" });
				let sampled_targets = [];
				for (let i = 0; i < target_raster.data.length; i += 7) {
					let local_value = target_raster.data[i];
					if (local_value > 0 && !isNaN(local_value)) {
						sampled_targets.push(local_value);
					}
				}
				
				if (sampled_targets.length > 0) {
					sampled_targets.sort((a, b) => a - b);
					let local_min = sampled_targets[Math.floor(sampled_targets.length * 0.01)];
					let local_max = sampled_targets[Math.floor(sampled_targets.length * 0.99)];
					let local_count = sampled_targets.length * 7;
					
					yearly_target_stats[year] = { min: local_min, max: local_max, sample_size: local_count };
					if (local_min < global_min) global_min = local_min;
					if (local_max > global_max) global_max = local_max;
				}
			}
			
			if (global_min === Infinity) continue;
			
			await GeoPNG.processTimeseriesParallel({
				items: years,
				concurrency: options.concurrency || 4,
				name: `births_deaths_OLS D_normaliseOLSRasters (${variable_obj.actual_prefix})`,
				handler: async (year) => {
					let popc_path = `${sf.input_popc_folder}stadester_population_${year}.png`;
					if (!fs.existsSync(popc_path)) return;
					
					let ols_path = `${variable_obj.ols_folder}ols_${variable_obj.actual_prefix}_${year}.png`;
					let normalised_path = `${variable_obj.normalised_folder}normalised_${variable_obj.actual_prefix}_${year}.png`;
					let bounds_path = `${this.intermediate_bounds}bounds_${variable_obj.actual_prefix}_${year}.json`;
					
					if (!fs.existsSync(ols_path)) return;
					if (!overwrite && fs.existsSync(normalised_path) && fs.existsSync(bounds_path)) return;
					
					let popc_raster = GeoPNG.loadNumberRasterImage(popc_path, { format: "float32" });
					let ols_raster = GeoPNG.loadNumberRasterImage(ols_path, { format: "float32" });
					
					let local_stats = yearly_target_stats[year];
					let has_targets = (local_stats !== undefined);
					let sample_size = (local_stats) ? local_stats.sample_size : 0;
					let target_min = (local_stats) ? local_stats.min : global_min;
					let target_max = (local_stats) ? local_stats.max : global_max;
					
					let uncertainty_weight = Math.exp(-sample_size/15);
					target_min = Math.max(0, target_min - ((target_min - global_min)*uncertainty_weight));
					target_max = target_max + ((global_max - target_max)*uncertainty_weight);
					
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
					let mean = sum/N;
					let sq_sum = 0;
					for (let i = 0; i < N; i++) sq_sum += Math.pow(valid_pixels[i] - mean, 2);
					let std = Math.sqrt(sq_sum/N);
					
					let q1 = valid_pixels[Math.floor(N*0.25)];
					let q3 = valid_pixels[Math.floor(N*0.75)];
					let iqr = q3 - q1;
					let alpha = (iqr > 1e-5) ? iqr : ((std > 1e-5) ? std : 0.01);
					
					let t_lower = q1 - (1.5*alpha);
					let t_upper = q3 + (1.5*alpha);
					
					let regularise = function (x) {
						if (x > t_upper) return t_upper + alpha*Math.log(1 + ((x - t_upper)/alpha));
						if (x < t_lower) return t_lower - alpha*Math.log(1 + ((t_lower - x)/alpha));
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
							let unit_value = (reg_range > 0) ? ((local_regularised - reg_min)/reg_range) : 0.5;
							normalised_map[i] = Math.max(0, Math.min(1, unit_value));
						}
					}
					
					GeoPNG.saveNumberRasterImage({
						file_path: normalised_path,
						format: "float32",
						width: ols_raster.width,
						height: ols_raster.height,
						function: (local_index) => normalised_map[local_index]
					});
					
					fs.writeFileSync(bounds_path, JSON.stringify({
						year: year,
						has_targets: has_targets,
						target_min: target_min,
						target_max: target_max,
						sample_size: sample_size
					}));
					
					console.log(`- Normalised OLS raster: ${normalised_path}`);
				}
			});
		}
	}
	
	static async E_clampToStadester (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;

		//Declare local instance variables
		let sf = age_sex.sf();
		let variables_obj = this._getVariablesObj();
		let years = landuse_HYDE.sorted_hyde_years;
		if (options.years) years = years.filter(y => options.years.includes(y));
		
		await GeoPNG.processTimeseriesParallel({
			items: years,
			concurrency: options.concurrency || 4,
			name: "births_deaths_OLS E_clampToStadester",
			handler: async (year) => {
				let popc_path = `${sf.input_popc_folder}stadester_population_${year}.png`;
				if (!fs.existsSync(popc_path)) return;
				
				let popc_raster = GeoPNG.loadNumberRasterImage(popc_path, { format: "float32" });
				let denominator_cache = {};
				
				// 1. Process all variables into memory first to get the RAW working aggregates
				let raw_data = {};
				let skip_year = false;
				
				let variable_keys = Object.keys(variables_obj);
				for (let v = 0; v < variable_keys.length; v++) {
					let v_key = variable_keys[v];
					let variable_obj = variables_obj[v_key];
					let normalised_path = `${variable_obj.normalised_folder}normalised_${variable_obj.actual_prefix}_${year}.png`;
					let bounds_path = `${this.intermediate_bounds}bounds_${variable_obj.actual_prefix}_${year}.json`;
					let output_path = `${variable_obj.output_folder}${variable_obj.actual_prefix}_${year}.png`;
					
					if (!fs.existsSync(normalised_path) || !fs.existsSync(bounds_path)) { skip_year = true; break; }
					if (!overwrite && fs.existsSync(output_path)) continue;
					
					let cache_key = variable_obj.denominator + (variable_obj.sex || "");
					if (!denominator_cache[cache_key]) {
						denominator_cache[cache_key] = this._getDenominatorArray(variable_obj, year);
					}
					let denominator_array = denominator_cache[cache_key];
					if (!denominator_array) { skip_year = true; break; }
					
					let normalised_raster = GeoPNG.loadNumberRasterImage(normalised_path, { format: "float32" });
					let bounds_obj = JSON.parse(fs.readFileSync(bounds_path, "utf8"));
					let counts_array = new Float32Array(normalised_raster.data.length);
					
					let target_min = bounds_obj.target_min || 0;
					let target_max = bounds_obj.target_max || 0;
					
					for (let i = 0; i < normalised_raster.data.length; i++) {
						if (popc_raster.data[i] <= 0) continue;
						
						let local_normalised = normalised_raster.data[i];
						if (isNaN(local_normalised) || local_normalised <= 0) continue;
						
						let local_denominator = denominator_array[i];
						if (local_denominator <= 0) continue;
						
						let local_fraction = target_min;
						if (target_max > target_min) {
							local_fraction = target_min + local_normalised * (target_max - target_min);
						}
						
						let count = local_fraction * local_denominator;
						if (variable_obj.denominator === "cohort_00") {
							count = Math.min(count, 1.5 * local_denominator);
						} else {
							count = Math.min(count, popc_raster.data[i]); // Deaths cannot exceed population
						}
						
						counts_array[i] = count;
					}
					
					raw_data[v_key] = {
						variable_obj: variable_obj,
						counts_array: counts_array,
						normalised_raster: normalised_raster,
						output_path: output_path
					};
				}
				
				if (skip_year) return;
				
				// 2. THE SEX-SANE REDISTRIBUTION (Intercepting the working aggregates)
				if (raw_data.male_deaths && raw_data.female_deaths) {
					let m_counts = raw_data.male_deaths.counts_array;
					let f_counts = raw_data.female_deaths.counts_array;
					let m_norm = raw_data.male_deaths.normalised_raster.data;
					let f_norm = raw_data.female_deaths.normalised_raster.data;
					
					for (let i = 0; i < popc_raster.data.length; i++) {
						if (popc_raster.data[i] <= 0) continue;
						
						let raw_m = m_counts[i] || 0;
						let raw_f = f_counts[i] || 0;
						let total = raw_m + raw_f;
						
						if (total > 0) {
							let n_m = (isNaN(m_norm[i]) || m_norm[i] < 0) ? 0 : m_norm[i];
							let n_f = (isNaN(f_norm[i]) || f_norm[i] < 0) ? 0 : f_norm[i];
							let norm_sum = n_m + n_f;
							
							let ratio_m = (norm_sum > 0) ? (n_m / norm_sum) : 0.5;
							m_counts[i] = total * ratio_m;
							f_counts[i] = total * (1.0 - ratio_m);
						}
					}
				}
				
				// 2.5. FLUX RECONCILIATION AGAINST MIGRATION RESIDUAL
				let migration_path = `${this.output_net_migration_folder}net_migration_${year}.png`;
				let m_female_path = `${this.output_female_migration_folder}female_net_migration_${year}.png`;
				let m_male_path = `${this.output_male_migration_folder}male_net_migration_${year}.png`;
				let delta_path = `${population_Stadester_transform.delta_total_population_folder}delta_total_population_${year}.png`;
				
				let m_raster_updated = false;
				let m_raster = null, mf_raster = null, mm_raster = null;
				
				if (fs.existsSync(migration_path) && fs.existsSync(m_female_path) && fs.existsSync(m_male_path) && fs.existsSync(delta_path) && raw_data.births && raw_data.male_deaths && raw_data.female_deaths) {
					m_raster = GeoPNG.loadNumberRasterImage(migration_path, { format: "float32" });
					mf_raster = GeoPNG.loadNumberRasterImage(m_female_path, { format: "float32" });
					mm_raster = GeoPNG.loadNumberRasterImage(m_male_path, { format: "float32" });
					let d_raster = GeoPNG.loadNumberRasterImage(delta_path, { format: "float32" });
					
					let b_counts = raw_data.births.counts_array;
					let md_counts = raw_data.male_deaths.counts_array;
					let fd_counts = raw_data.female_deaths.counts_array;
					
					let y_idx = years.indexOf(year);
					let year_gap = 1;
					if (y_idx > 0) year_gap = year - years[y_idx - 1];
					
					let b_denominator = denominator_cache["cohort_00"];
					let md_denominator = denominator_cache["cohort_declinem"];
					let fd_denominator = denominator_cache["cohort_declinef"];
					
					for (let i = 0; i < popc_raster.data.length; i++) {
						let pop = popc_raster.data[i];
						if (pop <= 0) continue;
						
						let m_val = m_raster.data[i];
						let d_val = d_raster.data[i];
						if (isNaN(m_val) || isNaN(d_val)) continue;
						
						let annualized_d_val = d_val / year_gap;
						
						let b_raw = b_counts[i] || 0;
						let md_raw = md_counts[i] || 0;
						let fd_raw = fd_counts[i] || 0;
						let d_raw = md_raw + fd_raw;
						
						let ng_target = annualized_d_val - m_val;
						let delta_ng = ng_target - (b_raw - d_raw);
						
						let b_final = b_raw;
						let d_final = d_raw;
						
						if (delta_ng > 0) {
							// Population growing faster than OLS predicts -> baby boom
							b_final += delta_ng;
						} else if (delta_ng < 0) {
							// Population shrinking faster than OLS predicts -> mortality crisis
							d_final -= delta_ng;
						}
						
						// CLAMP TO BIOLOGICAL PHYSICAL LIMITS
						let max_b = (b_denominator && !isNaN(b_denominator[i])) ? (1.5 * b_denominator[i]) : 0;
						let max_d = pop; // Deaths can never exceed the living population
						
						let min_b = 0;
						let min_d = 0;
						
						if (b_final > max_b) b_final = max_b;
						if (b_final < min_b) b_final = min_b;
						if (d_final > max_d) d_final = max_d;
						if (d_final < min_d) d_final = min_d;
						
						let clamped_ng = b_final - d_final;
						
						// The residual discrepancy MUST be absorbed by migration
						let m_new = annualized_d_val - clamped_ng;
						let m_diff = m_new - m_val;
						
						if (Math.abs(m_diff) > 1) {
							m_raster.data[i] = m_new;
							m_raster_updated = true;
							
							let mf_val = isNaN(mf_raster.data[i]) ? 0 : mf_raster.data[i];
							let mm_val = isNaN(mm_raster.data[i]) ? 0 : mm_raster.data[i];
							
							let m_total = mf_val + mm_val;
							let f_ratio = (Math.abs(m_total) > 0) ? (mf_val / m_total) : 0.488;
							let m_ratio = (Math.abs(m_total) > 0) ? (mm_val / m_total) : 0.512;
							
							mf_raster.data[i] = mf_val + (m_diff * f_ratio);
							mm_raster.data[i] = mm_val + (m_diff * m_ratio);
						}
						
						b_counts[i] = b_final;
						
						if (d_raw > 0) {
							md_counts[i] = d_final * (md_raw / d_raw);
							fd_counts[i] = d_final * (fd_raw / d_raw);
						} else {
							md_counts[i] = d_final * 0.512;
							fd_counts[i] = d_final * 0.488;
						}
					}
				}

				// 3. Write final clamped rasters to disk, preserving empirical actuals where available
				let loaded_keys = Object.keys(raw_data);
				for (let v = 0; v < loaded_keys.length; v++) {
					let v_key = loaded_keys[v];
					let data = raw_data[v_key];
					let counts_array = data.counts_array;
					let output_path = data.output_path;
					let variable_obj = data.variable_obj;
					
					let actual_path = this._getActualPath(variable_obj, year);
					let actual_raster = (actual_path) ? GeoPNG.loadNumberRasterImage(actual_path, { format: "float32" }) : null;
					
					GeoPNG.saveNumberRasterImage({
						file_path: output_path,
						format: "float32",
						width: popc_raster.width,
						height: popc_raster.height,
						function: (local_index) => {
							let local_pop = popc_raster.data[local_index];
							if (local_pop <= 0) return 0;
							
							if (actual_raster) {
								let local_actual = actual_raster.data[local_index];
								if (!isNaN(local_actual) && local_actual > 0) return local_actual;
							}
							
							return counts_array[local_index] || 0;
						}
					});
					
					console.log(`- Saved clamped raster: ${output_path}`);
				}
				
				// 4. Save updated migration rasters if flux reconciliation pushed residuals back to them
				if (m_raster_updated) {
					GeoPNG.saveNumberRasterImage({ file_path: migration_path, format: "float32", width: popc_raster.width, height: popc_raster.height, function: (i) => m_raster.data[i] });
					GeoPNG.saveNumberRasterImage({ file_path: m_female_path, format: "float32", width: popc_raster.width, height: popc_raster.height, function: (i) => mf_raster.data[i] });
					GeoPNG.saveNumberRasterImage({ file_path: m_male_path, format: "float32", width: popc_raster.width, height: popc_raster.height, function: (i) => mm_raster.data[i] });
					console.log(`- Updated migration rasters to absorb residual biological overflow for ${year}`);
				}
			}
		});
	}
	
	static async processRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		if (!options.exclude) options.exclude = [];
		let skip_training = (options.skip_training || options.use_existing_models || options.train === false);
		
		//Declare local instance variables
		let all_folders = [
			this.intermediate_birth_targets,
			this.intermediate_female_death_targets,
			this.intermediate_male_death_targets,
			this.intermediate_ols_births,
			this.intermediate_ols_female_deaths,
			this.intermediate_ols_male_deaths,
			this.intermediate_normalised_births,
			this.intermediate_normalised_female_deaths,
			this.intermediate_normalised_male_deaths,
			this.intermediate_bounds,
			this.output_births_folder,
			this.output_female_deaths_folder,
			this.output_male_deaths_folder,
			this.output_female_migration_folder,
			this.output_male_migration_folder,
			this.output_net_migration_folder
		];
		for (let i = 0; i < all_folders.length; i++)
			if (!fs.existsSync(all_folders[i])) fs.mkdirSync(all_folders[i], { recursive: true });
		
		if (!options.exclude.includes("A") && !skip_training) await this.A_generateTargetRasters(options);
		if (!options.exclude.includes("B") && !skip_training) await this.B_trainOLSModels(options);
		if (!options.exclude.includes("C")) await this.C_generateOLSRasters(options);
		if (!options.exclude.includes("D")) await this.D_normaliseOLSRasters(options);
		if (!options.exclude.includes("E")) await this.E_clampToStadester(options);
	}
};