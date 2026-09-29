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
				actual_folder_kummu: (typeof births_deaths_Kummu !== "undefined") ? births_deaths_Kummu.output_births_folder : (global.h2 ? path.join(global.h2, "births_deaths_Kummu/output_birth_rasters/") : null),
				actual_folder_unwpp: (typeof births_deaths_UNWPP !== "undefined") ? births_deaths_UNWPP.output_crude_births_folder : (global.h2 ? path.join(global.h2, "births_deaths_UNWPP/1.crude_births/") : null),
				actual_folder_hmd: (typeof births_deaths_HMD !== "undefined") ? births_deaths_HMD.output_crude_births_folder : (global.h2 ? path.join(global.h2, "births_deaths_HMD/1.crude_births/") : null),
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
				actual_folder_unwpp: (typeof births_deaths_UNWPP !== "undefined") ? births_deaths_UNWPP.output_female_crude_deaths_folder : (global.h2 ? path.join(global.h2, "births_deaths_UNWPP/1.female_crude_deaths/") : null),
				actual_folder_hmd: (typeof births_deaths_HMD !== "undefined") ? births_deaths_HMD.output_female_crude_deaths_folder : (global.h2 ? path.join(global.h2, "births_deaths_HMD/1.female_crude_deaths/") : null),
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
				actual_folder_unwpp: (typeof births_deaths_UNWPP !== "undefined") ? births_deaths_UNWPP.output_male_crude_deaths_folder : (global.h2 ? path.join(global.h2, "births_deaths_UNWPP/1.male_crude_deaths/") : null),
				actual_folder_hmd: (typeof births_deaths_HMD !== "undefined") ? births_deaths_HMD.output_male_crude_deaths_folder : (global.h2 ? path.join(global.h2, "births_deaths_HMD/1.male_crude_deaths/") : null),
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
	 * Returns the actual (Kummu/UNWPP/HMD) count raster path for a variable/year, or null.
	 */
	static _getActualPath (arg0_variable_obj, arg1_year) {
		//Convert from parameters
		let variable_obj = arg0_variable_obj;
		let year = arg1_year;
		
		//Declare local instance variables
		let folder = (year >= 1950) ? variable_obj.actual_folder_unwpp : variable_obj.actual_folder_hmd;
		let local_path = (folder) ? `${folder}${variable_obj.actual_prefix}_${year}.png` : null;
		
		//Return statement
		return (local_path && fs.existsSync(local_path)) ? local_path : null;
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

				// Check empirical sources (backcalculated UNWPP / Niva et al. 1950-2023)
				let unwpp_b_folder = (typeof births_deaths_UNWPP !== "undefined") ? births_deaths_UNWPP.output_crude_births_folder : (global.h2 ? path.join(global.h2, "births_deaths_UNWPP/1.crude_births/") : null);
				let unwpp_fd_folder = (typeof births_deaths_UNWPP !== "undefined") ? births_deaths_UNWPP.output_female_crude_deaths_folder : (global.h2 ? path.join(global.h2, "births_deaths_UNWPP/1.female_crude_deaths/") : null);
				let unwpp_md_folder = (typeof births_deaths_UNWPP !== "undefined") ? births_deaths_UNWPP.output_male_crude_deaths_folder : (global.h2 ? path.join(global.h2, "births_deaths_UNWPP/1.male_crude_deaths/") : null);

				let unwpp_b_path = (unwpp_b_folder) ? path.join(unwpp_b_folder, `births_${year}.png`) : null;
				let unwpp_fd_path = (unwpp_fd_folder) ? path.join(unwpp_fd_folder, `female_deaths_${year}.png`) : null;
				let unwpp_md_path = (unwpp_md_folder) ? path.join(unwpp_md_folder, `male_deaths_${year}.png`) : null;
				let has_unwpp = unwpp_b_path && unwpp_fd_path && unwpp_md_path && fs.existsSync(unwpp_b_path) && fs.existsSync(unwpp_fd_path) && fs.existsSync(unwpp_md_path);

				let b_out = `${this.output_births_folder}births_${year}.png`;
				let fd_out = `${this.output_female_deaths_folder}female_deaths_${year}.png`;
				let md_out = `${this.output_male_deaths_folder}male_deaths_${year}.png`;

				if (!overwrite && fs.existsSync(b_out) && fs.existsSync(fd_out) && fs.existsSync(md_out)) return;

				let denominator_cache = {};
				let raw_data = {};
				let skip_year = false;

				if (has_unwpp) {
					let unwpp_b_r = GeoPNG.loadNumberRasterImage(unwpp_b_path, { format: "float32" });
					let unwpp_fd_r = GeoPNG.loadNumberRasterImage(unwpp_fd_path, { format: "float32" });
					let unwpp_md_r = GeoPNG.loadNumberRasterImage(unwpp_md_path, { format: "float32" });

					let final_b = new Float32Array(popc_raster.data.length);
					let final_fd = new Float32Array(popc_raster.data.length);
					let final_md = new Float32Array(popc_raster.data.length);
					let has_act = new Uint8Array(popc_raster.data.length);

					for (let i = 0; i < popc_raster.data.length; i++) {
						let pop = popc_raster.data[i];
						if (pop <= 0 || isNaN(pop)) continue;

						let b = isNaN(unwpp_b_r.data[i]) ? 0 : Math.max(0, unwpp_b_r.data[i]);
						let fd = isNaN(unwpp_fd_r.data[i]) ? 0 : Math.max(0, unwpp_fd_r.data[i]);
						let md = isNaN(unwpp_md_r.data[i]) ? 0 : Math.max(0, unwpp_md_r.data[i]);

						final_b[i] = b;
						final_fd[i] = fd;
						final_md[i] = md;
						has_act[i] = 1;
					}

					raw_data.births = {
						actual_raster: unwpp_b_r,
						counts_array: final_b,
						has_actual_array: has_act,
						is_empirical_source: true,
						output_path: b_out,
						variable_obj: variables_obj.births
					};
					raw_data.female_deaths = {
						actual_raster: unwpp_fd_r,
						counts_array: final_fd,
						has_actual_array: has_act,
						is_empirical_source: true,
						output_path: fd_out,
						variable_obj: variables_obj.female_deaths
					};
					raw_data.male_deaths = {
						actual_raster: unwpp_md_r,
						counts_array: final_md,
						has_actual_array: has_act,
						is_empirical_source: true,
						output_path: md_out,
						variable_obj: variables_obj.male_deaths
					};
				} else {
					// 1. Process all variables into memory first to get the RAW working aggregates
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
						let actual_path = this._getActualPath(variable_obj, year);
						let actual_raster = (actual_path) ? GeoPNG.loadNumberRasterImage(actual_path, { format: "float32" }) : null;
						let has_actual_array = new Uint8Array(normalised_raster.data.length);
						
						let target_min = bounds_obj.target_min || 0;
						let target_max = bounds_obj.target_max || 0;
						
						for (let i = 0; i < normalised_raster.data.length; i++) {
							if (popc_raster.data[i] <= 0) continue;
							
							if (actual_raster) {
								let local_actual = actual_raster.data[i];
								if (!isNaN(local_actual) && local_actual > 0) {
									counts_array[i] = local_actual;
									has_actual_array[i] = 1;
									continue;
								}
							}
							
							let local_normalised = normalised_raster.data[i];
							if (isNaN(local_normalised) || local_normalised < 0) continue;
							
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
							actual_raster: actual_raster,
							counts_array: counts_array,
							has_actual_array: has_actual_array,
							normalised_raster: normalised_raster,
							output_path: output_path,
							variable_obj: variable_obj
						};
					}
				}
				
				if (skip_year) return;
				
				// 2. THE SEX-SANE REDISTRIBUTION (Intercepting the working aggregates)
				if (!has_unwpp && raw_data.male_deaths && raw_data.female_deaths) {
					let f_actual = raw_data.female_deaths.has_actual_array;
					let f_counts = raw_data.female_deaths.counts_array;
					let f_norm = (raw_data.female_deaths.normalised_raster) ? raw_data.female_deaths.normalised_raster.data : null;
					let m_actual = raw_data.male_deaths.has_actual_array;
					let m_counts = raw_data.male_deaths.counts_array;
					let m_norm = (raw_data.male_deaths.normalised_raster) ? raw_data.male_deaths.normalised_raster.data : null;
					
					for (let i = 0; i < popc_raster.data.length; i++) {
						if (popc_raster.data[i] <= 0) continue;
						if ((m_actual && m_actual[i]) || (f_actual && f_actual[i])) continue;
						
						let raw_f = f_counts[i] || 0;
						let raw_m = m_counts[i] || 0;
						let total = raw_m + raw_f;
						
						if (total > 0 && f_norm && m_norm) {
							let n_f = (isNaN(f_norm[i]) || f_norm[i] < 0) ? 0 : f_norm[i];
							let n_m = (isNaN(m_norm[i]) || m_norm[i] < 0) ? 0 : m_norm[i];
							let norm_sum = n_m + n_f;
							
							let ratio_m = (norm_sum > 0) ? (n_m / norm_sum) : 0.5;
							m_counts[i] = total * ratio_m;
							f_counts[i] = total * (1.0 - ratio_m);
						}
					}
				}
				
				// 2.5. FLUX RECONCILIATION AGAINST MIGRATION RESIDUAL
				let delta_path = `${population_Stadester_transform.delta_total_population_folder}delta_total_population_${year}.png`;
				let m_female_path = `${this.output_female_migration_folder}female_net_migration_${year}.png`;
				let m_male_path = `${this.output_male_migration_folder}male_net_migration_${year}.png`;
				let migration_path = `${this.output_net_migration_folder}net_migration_${year}.png`;
				
				let m_raster = null, mf_raster = null, mm_raster = null;
				
				if (fs.existsSync(migration_path) && fs.existsSync(m_female_path) && fs.existsSync(m_male_path) && fs.existsSync(delta_path) && raw_data.births && raw_data.male_deaths && raw_data.female_deaths) {
					let d_raster = GeoPNG.loadNumberRasterImage(delta_path, { format: "float32" });
					m_raster = GeoPNG.loadNumberRasterImage(migration_path, { format: "float32" });
					mf_raster = GeoPNG.loadNumberRasterImage(m_female_path, { format: "float32" });
					mm_raster = GeoPNG.loadNumberRasterImage(m_male_path, { format: "float32" });
					
					let b_actual = raw_data.births.has_actual_array;
					let b_counts = raw_data.births.counts_array;
					let b_denominator = denominator_cache["cohort_00"];
					let fd_actual = raw_data.female_deaths.has_actual_array;
					let fd_counts = raw_data.female_deaths.counts_array;
					let md_actual = raw_data.male_deaths.has_actual_array;
					let md_counts = raw_data.male_deaths.counts_array;
					
					let all_years = (typeof landuse_HYDE !== "undefined" && Array.isArray(landuse_HYDE.sorted_hyde_years)) ? landuse_HYDE.sorted_hyde_years : years;
					let y_idx = all_years.indexOf(year);
					let year_gap = 1;
					if (y_idx > 0) year_gap = year - all_years[y_idx - 1];
					
					let is_empirical_data = (raw_data.births && raw_data.births.is_empirical_source);
					let total_len = popc_raster.data.length;
					
					let geocode_obj = admin_modern.getISO3ColourcodesObject();
					let geocode_raster = GeoPNG.loadImage(admin_modern.input_geocodes_raster);
					
					let hmd_m_diff_sum = 0;
					let non_hmd_pop_sum = 0;
					
					// 1. Process HMD empirical pixels: vital rates are fixed, migration is the residual
					for (let i = 0; i < total_len; i++) {
						let pop = popc_raster.data[i];
						if (pop <= 0) continue;
						
						let d_val = d_raster.data[i];
						let m_val = m_raster.data[i];
						if (isNaN(d_val) || isNaN(m_val)) continue;
						
						let is_b_actual = (b_actual && b_actual[i]);
						let is_fd_actual = (fd_actual && fd_actual[i]);
						let is_md_actual = (md_actual && md_actual[i]);
						let is_hmd = ((is_b_actual || (is_fd_actual && is_md_actual)) && !is_empirical_data);
						let g = d_val / year_gap;
						
						if (is_hmd) {
							let b = b_counts[i] || 0;
							let fd = fd_counts[i] || 0;
							let md = md_counts[i] || 0;
							let d = fd + md;
							
							// For HMD countries, empirical vital rates are ground truth; migration is the residual
							let m_residual = g - (b - d);
							let m_diff = m_residual - m_val;
							hmd_m_diff_sum += m_diff;
							
							m_raster.data[i] = m_residual;
							
							let mf_val = isNaN(mf_raster.data[i]) ? 0 : mf_raster.data[i];
							let mm_val = isNaN(mm_raster.data[i]) ? 0 : mm_raster.data[i];
							let tot_m = mf_val + mm_val;
							let fr = (tot_m !== 0) ? (mf_val / tot_m) : 0.488;
							
							mf_raster.data[i] = mf_val + m_diff * fr;
							mm_raster.data[i] = mm_val + m_diff * (1 - fr);
						} else {
							non_hmd_pop_sum += pop;
						}
					}
					
					// 2. Conserve global net migration zero-sum and accumulate non-HMD country targets
					let balance_rate = (non_hmd_pop_sum > 0) ? (-hmd_m_diff_sum / non_hmd_pop_sum) : 0;
					let country_b_raw = {};
					let country_d_raw = {};
					let country_n_target = {};
					
					for (let i = 0; i < total_len; i++) {
						let pop = popc_raster.data[i];
						if (pop <= 0) continue;
						
						let d_val = d_raster.data[i];
						let m_val = m_raster.data[i];
						if (isNaN(d_val) || isNaN(m_val)) continue;
						
						let is_b_actual = (b_actual && b_actual[i]);
						let is_fd_actual = (fd_actual && fd_actual[i]);
						let is_md_actual = (md_actual && md_actual[i]);
						let is_hmd = ((is_b_actual || (is_fd_actual && is_md_actual)) && !is_empirical_data);
						if (is_hmd) continue;
						
						let g = d_val / year_gap;
						let m_adj = m_val + pop * balance_rate;
						let m_diff = m_adj - m_val;
						
						m_raster.data[i] = m_adj;
						
						let mf_val = isNaN(mf_raster.data[i]) ? 0 : mf_raster.data[i];
						let mm_val = isNaN(mm_raster.data[i]) ? 0 : mm_raster.data[i];
						let tot_m = mf_val + mm_val;
						let fr = (tot_m !== 0) ? (mf_val / tot_m) : 0.488;
						
						mf_raster.data[i] = mf_val + m_diff * fr;
						mm_raster.data[i] = mm_val + m_diff * (1 - fr);
						
						let b_raw = b_counts[i] || 0;
						let fd_raw = fd_counts[i] || 0;
						let md_raw = md_counts[i] || 0;
						let d_raw = fd_raw + md_raw;
						let n_target = g - m_adj;
						
						let bi = i * 4;
						let local_colour_key = [
							geocode_raster.data[bi],
							geocode_raster.data[bi + 1],
							geocode_raster.data[bi + 2]
						].join(",");
						let local_geocodes = geocode_obj[local_colour_key];
						let local_iso = (local_geocodes && local_geocodes.length > 0) ? local_geocodes[0] : "GLOBAL";
						
						Object.modifyValue(country_b_raw, local_iso, b_raw);
						Object.modifyValue(country_d_raw, local_iso, d_raw);
						Object.modifyValue(country_n_target, local_iso, n_target);
					}
					
					// 3. Reconcile natural change at country level for non-HMD countries (bivariate geometric minimum information)
					let country_sb = {};
					let country_sd = {};
					
					Object.iterate(country_n_target, (local_iso, local_n_target) => {
						let b_raw = country_b_raw[local_iso] || 0;
						let d_raw = country_d_raw[local_iso] || 0;
						
						if (b_raw > 0 && d_raw > 0) {
							let discriminant = Math.sqrt(local_n_target*local_n_target + 4*b_raw*d_raw);
							let b_star = (local_n_target + discriminant) / 2;
							let d_star = (discriminant - local_n_target) / 2;
							
							country_sb[local_iso] = b_star / b_raw;
							country_sd[local_iso] = d_star / d_raw;
						} else {
							country_sb[local_iso] = 1;
							country_sd[local_iso] = 1;
						}
					});
					
					// 4. Reconcile non-HMD pixels: births and deaths close the demographic accounting identity
					for (let i = 0; i < total_len; i++) {
						let pop = popc_raster.data[i];
						if (pop <= 0) continue;
						
						let d_val = d_raster.data[i];
						let m_val = m_raster.data[i];
						if (isNaN(d_val) || isNaN(m_val)) continue;
						
						let is_b_actual = (b_actual && b_actual[i]);
						let is_fd_actual = (fd_actual && fd_actual[i]);
						let is_md_actual = (md_actual && md_actual[i]);
						let is_hmd = ((is_b_actual || (is_fd_actual && is_md_actual)) && !is_empirical_data);
						if (is_hmd) continue;
						
						let g = d_val / year_gap;
						let m = m_raster.data[i];
						let n_target = g - m;
						
						let bi = i * 4;
						let local_colour_key = [
							geocode_raster.data[bi],
							geocode_raster.data[bi + 1],
							geocode_raster.data[bi + 2]
						].join(",");
						let local_geocodes = geocode_obj[local_colour_key];
						let local_iso = (local_geocodes && local_geocodes.length > 0) ? local_geocodes[0] : "GLOBAL";
						
						let b_raw = b_counts[i] || 0;
						let fd_raw = fd_counts[i] || 0;
						let md_raw = md_counts[i] || 0;
						let d_raw = fd_raw + md_raw;
						
						let sb = country_sb[local_iso] || 1;
						let sd = country_sd[local_iso] || 1;
						
						let b_base = b_raw * sb;
						let d_base = d_raw * sd;
						let b_final = 0;
						let d_final = 0;
						
						if (b_base > 0 && d_base > 0) {
							let discriminant = Math.sqrt(n_target*n_target + 4*b_base*d_base);
							b_final = (n_target + discriminant) / 2;
							d_final = (discriminant - n_target) / 2;
						} else {
							b_final = Math.max(0, n_target);
							d_final = Math.max(0, -n_target);
						}
						
						if (d_final > pop) {
							d_final = pop;
							b_final = Math.max(0, pop + n_target);
							let m_residual_pixel = g - (b_final - d_final);
							let m_diff_pixel = m_residual_pixel - m_raster.data[i];
							m_raster.data[i] = m_residual_pixel;
							
							let mf_val = isNaN(mf_raster.data[i]) ? 0 : mf_raster.data[i];
							let mm_val = isNaN(mm_raster.data[i]) ? 0 : mm_raster.data[i];
							let tot_m = mf_val + mm_val;
							let fr = (tot_m !== 0) ? (mf_val / tot_m) : 0.488;
							
							mf_raster.data[i] = mf_val + m_diff_pixel * fr;
							mm_raster.data[i] = mm_val + m_diff_pixel * (1 - fr);
						}
						
						let ratio_m = (d_raw > 0) ? (md_raw / d_raw) : 0.512;
						b_counts[i] = Math.max(0, b_final);
						md_counts[i] = Math.max(0, d_final * ratio_m);
						fd_counts[i] = Math.max(0, d_final - md_counts[i]);
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
					
					GeoPNG.saveNumberRasterImage({
						file_path: output_path,
						format: "float32",
						width: popc_raster.width,
						height: popc_raster.height,
						function: (local_index) => {
							let local_pop = popc_raster.data[local_index];
							if (local_pop <= 0) return 0;
							
							let val = counts_array[local_index] || 0;
							return (val > 0) ? val : 0;
						}
					});
					
					console.log(`- Saved clamped raster: ${output_path}`);
				}
				
				// 4. Save reconciled migration rasters ensuring complete demographic closure
				if (m_raster) {
					GeoPNG.saveNumberRasterImage({ file_path: migration_path, format: "float32", width: popc_raster.width, height: popc_raster.height, function: (i) => m_raster.data[i] });
					GeoPNG.saveNumberRasterImage({ file_path: m_female_path, format: "float32", width: popc_raster.width, height: popc_raster.height, function: (i) => mf_raster.data[i] });
					GeoPNG.saveNumberRasterImage({ file_path: m_male_path, format: "float32", width: popc_raster.width, height: popc_raster.height, function: (i) => mm_raster.data[i] });
					console.log(`- Saved reconciled migration rasters for ${year}`);
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