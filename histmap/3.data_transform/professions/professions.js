global.professions = class {
	static cf = `${h3}/professions/`;
	
	static covariates_obj = () => ({
		...age_sex.covariates_obj,
		"gini": (y) => [`${gini_Eoscala.output_rasters}gini_${y}.png`, "float32"],
		"lfpr_f": (y) => [`${LFPR_OLS.output_lfpr_rates}lfpr_f_${y}.png`, "float32"],
		"lfpr_m": (y) => [`${LFPR_OLS.output_lfpr_rates}lfpr_m_${y}.png`, "float32"],
	});
	
	// Paths
	static standardised_targets_folder = `${this.cf}/0.standardised_targets/`;
	static intermediate_logit_folder = `${this.cf}/1.multinomial_logit/`;
	static intermediate_logit_rasters = `${this.cf}/2.logit_rasters/`;
	static output_percentages = `${this.cf}/3.percentages/`;
	static output_aggregates = `${this.cf}/4.aggregates/`;
	
	static sexes = ["m", "f"];
	static categories = ["agriculture", "manufacturing", "services", "informal_labour", "not_in_work"];
	static olivetti_categories = ["agriculture", "manufacturing", "services", "informal_labour"];
	static working_cohorts = ["15", "20", "25", "30", "35", "40", "45", "50", "55", "60", "65", "70", "75", "80"];
	
	/**
	 * Prepares the target absolute populations for the MNL. Calculates `not_in_work` as the structural
	 * LFPR residual and deletes completely transparent/0-data Olivetti rasters.
	 */
	static async A_standardiseTargets (arg0_options) {
		let options = (arg0_options) ? arg0_options : {};
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;

		if (!fs.existsSync(this.standardised_targets_folder)) fs.mkdirSync(this.standardised_targets_folder, { recursive: true });
		
		let years = landuse_HYDE.sorted_hyde_years.filter(y => y >= 1750 && y <= 2025);
		
		for (let y = 0; y < years.length; y++) {
			let year = years[y];
			
			for (let s = 0; s < this.sexes.length; s++) {
				let sex = this.sexes[s];
				
				let all_exist = true;
				for (let i = 0; i < this.categories.length; i++) {
					if (!fs.existsSync(`${this.standardised_targets_folder}global_${this.categories[i]}_${sex}_${year}.png`)) all_exist = false;
				}
				if (!overwrite && all_exist) continue;
				
				let olivetti_rasters = {};
				let has_olivetti = true;
				
				for (let i = 0; i < this.olivetti_categories.length; i++) {
					let c = this.olivetti_categories[i];
					let path = `${professions_Olivetti.output_rasters}${c}_${sex}_${year}.png`;
					if (fs.existsSync(path)) {
						olivetti_rasters[c] = GeoPNG.loadNumberRasterImage(path, { format: "float32" });
					} else {
						has_olivetti = false;
					}
				}
				
				if (!has_olivetti) continue;
				
				let data_len = olivetti_rasters[this.olivetti_categories[0]].data.length;
				let sum_olivetti = 0;
				
				for (let i = 0; i < data_len; i++) {
					for (let j = 0; j < this.olivetti_categories.length; j++) {
						let val = olivetti_rasters[this.olivetti_categories[j]].data[i];
						if (!isNaN(val) && val > 0) sum_olivetti += val;
					}
				}
				
				// Zero Data Quarantine: Delete from original source and seamlessly skip training anchor
				if (sum_olivetti <= 0) {
					console.warn(`[CLEANUP] Stripping utterly empty Olivetti zero-data for ${sex} ${year}`);
					for (let i = 0; i < this.olivetti_categories.length; i++) {
						let path = `${professions_Olivetti.output_rasters}${this.olivetti_categories[i]}_${sex}_${year}.png`;
						if (fs.existsSync(path)) fs.unlinkSync(path);
					}
					continue;
				}
				
				let lfpr_path = `${LFPR_OLS.output_lfpr_rates}lfpr_${sex}_${year}.png`;
				if (!fs.existsSync(lfpr_path)) continue;
				let lfpr_raster = GeoPNG.loadNumberRasterImage(lfpr_path, { format: "float32" });
				
				let pop_raster = new Float32Array(data_len);
				for (let i = 0; i < this.working_cohorts.length; i++) {
					let cohort = this.working_cohorts[i];
					let cp = `${global.age_sex.output_rasters}${sex}_${cohort}_${year}.png`;
					
					if (fs.existsSync(cp)) {
						let c_raster = GeoPNG.loadNumberRasterImage(cp, { format: "float32" });
						for (let j = 0; j < data_len; j++) {
							let val = c_raster.data[j];
							if (!isNaN(val) && val > 0) pop_raster[j] += val;
						}
					}
				}
				
				for (let i = 0; i < this.categories.length; i++) {
					let c = this.categories[i];
					let out_path = `${this.standardised_targets_folder}global_${c}_${sex}_${year}.png`;
					
					GeoPNG.saveNumberRasterImage({
						file_path: out_path,
						format: "float32",
						width: lfpr_raster.width,
						height: lfpr_raster.height,
						function: (idx) => {
							let pop = pop_raster[idx];
							if (pop <= 0) return 0;
							
							if (c === "not_in_work") {
								let lfpr = lfpr_raster.data[idx];
								if (isNaN(lfpr)) lfpr = 0;
								return pop * Math.max(0, (1.0 - lfpr));
							} else {
								let rate = olivetti_rasters[c].data[idx];
								if (isNaN(rate)) rate = 0;
								return pop * rate;
							}
						}
					});
				}
				
				console.log(`Standardised MNL target anchors mapped for ${sex} ${year}.`);
				await Blacktraffic.yield();
			}
		}
	}
	
	/**
	 * Extracts valid spatial matrices for training categorical profession assignments via gradient descent.
	 * Only active labor categories (olivetti_categories) are extracted to explicitly prevent training on 'not_in_work'.
	 */
	static async B_trainMultinomialLogitModels (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
		
		//Declare local instance variables
		let cov_obj = this.covariates_obj();
		let items = [];
		let train_years = landuse_HYDE.sorted_hyde_years.filter(y => y >= 1750 && y <= 2025);
		
		if (!fs.existsSync(this.intermediate_logit_folder)) fs.mkdirSync(this.intermediate_logit_folder, { recursive: true });
		
		for (let s = 0; s < this.sexes.length; s++) {
			let sex = this.sexes[s];
			for (let y = 0; y < train_years.length; y++) {
				let year = train_years[y];
				let model_path = `${this.intermediate_logit_folder}multinomial_model_${sex}_${year}.json`;
				if (overwrite || !fs.existsSync(model_path))
					items.push({ sex: sex, year: year });
			}
		}
		
		if (items.length === 0) return [];
		
		//Return statement
		return await Statistics.trainMultinomialLogitModelsParallel(items, (item) => {
			let all_keys = Object.keys(cov_obj);
			let covariates_map = {};
			let format_year = item.year > 2023 ? 2023 : item.year;
			let model_path = `${this.intermediate_logit_folder}multinomial_model_${item.sex}_${item.year}.json`;
			let target_paths = {};
			
			for (let i = 0; i < all_keys.length; i++) {
				let k = all_keys[i];
				let info = cov_obj[k](format_year);
				covariates_map[k] = info;
			}
			
			for (let i = 0; i < this.olivetti_categories.length; i++) {
				let cat = this.olivetti_categories[i];
				target_paths[cat] = `${this.standardised_targets_folder}global_${cat}_${item.sex}_${item.year}.png`;
			}
			
			return {
				categories: this.olivetti_categories,
				covariates_map: covariates_map,
				model_path: model_path,
				options: {
					debug: true,
					lambda: Math.returnSafeNumber(options.lambda, 1e-4),
					learning_rate: Math.returnSafeNumber(options.learning_rate, 0.1),
					max_iterations: Math.returnSafeNumber(options.max_iterations, 50)
				},
				target_paths: target_paths
			};
		}, {
			concurrency: options.concurrency,
			name: "Professions Multinomial Logit Training"
		});
	}
	
	/**
	 * Averages MNL models to strip spatial volatility for extrapolations.
	 * An arithmetic mean of logit coefficients equates mathematically to a geometric mean of their odds ratios.
	 */
	static async C_mergeMultinomialLogitModels (arg0_options) {
		let options = (arg0_options) ? arg0_options : {};
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;

		let train_years = landuse_HYDE.sorted_hyde_years.filter(y => y >= 1750 && y <= 2025);
		
		for (let s = 0; s < this.sexes.length; s++) {
			let sex = this.sexes[s];
			let geomean_path = `${this.intermediate_logit_folder}multinomial_model_geomean_${sex}.json`;
			
			if (!overwrite && fs.existsSync(geomean_path)) continue;
			
			let models_loaded = 0;
			let geomean_sums = {};
			let ref_class = "";
			let valid_covariates = [];
			
			for (let y = 0; y < train_years.length; y++) {
				let year = train_years[y];
				let p = `${this.intermediate_logit_folder}multinomial_model_${sex}_${year}.json`;
				
				if (fs.existsSync(p)) {
					let m = JSON.parse(fs.readFileSync(p, "utf8"));
					models_loaded++;
					ref_class = m.reference_class;
					valid_covariates = m.covariates;
					
					Object.iterate(m.coefficients, (c_key, covs) => {
						if (!geomean_sums[c_key]) geomean_sums[c_key] = {};
						Object.iterate(covs, (cov_key, val) => {
							if (geomean_sums[c_key][cov_key] === undefined) geomean_sums[c_key][cov_key] = 0;
							geomean_sums[c_key][cov_key] += val;
						});
					});
				}
			}
			
			if (models_loaded === 0) continue;
			
			let geomean_model = {
				type: "multinomial_logit",
				classes: this.olivetti_categories,
				reference_class: ref_class,
				covariates: valid_covariates,
				coefficients: {}
			};
			
			Object.iterate(geomean_sums, (c_key, covs) => {
				geomean_model.coefficients[c_key] = {};
				Object.iterate(covs, (cov_key, val) => {
					geomean_model.coefficients[c_key][cov_key] = val / models_loaded;
				});
			});
			
			fs.writeFileSync(geomean_path, JSON.stringify(geomean_model, null, 2));
			console.log(`Geomean multinomial logit model established dynamically for sex (${sex}).`);
		}
	}
	
	/**
	 * Exclusively uses the Geomean model to project theoretical percent distributions across all temporal horizons.
	 */
	static async D_generateMultinomialLogitRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
		
		//Declare local instance variables
		let cov_obj = this.covariates_obj();
		let items = [];
		let years = landuse_HYDE.sorted_hyde_years;
		
		if (!fs.existsSync(this.intermediate_logit_rasters)) fs.mkdirSync(this.intermediate_logit_rasters, { recursive: true });
		
		for (let s = 0; s < this.sexes.length; s++) {
			let sex = this.sexes[s];
			let model_path = `${this.intermediate_logit_folder}multinomial_model_geomean_${sex}.json`;
			if (!fs.existsSync(model_path)) continue;
			
			for (let y = 0; y < years.length; y++) {
				let year = years[y];
				let out_base = `${this.intermediate_logit_rasters}logit_${sex}_${year}.png`;
				let check_path = out_base.replace(".png", `_class_${this.olivetti_categories[0]}.png`);
				if (overwrite || !fs.existsSync(check_path))
					items.push({ model_path: model_path, out_base: out_base, sex: sex, year: year });
			}
		}
		
		if (items.length === 0) return [];
		
		//Return statement
		return await Statistics.generateMultinomialRastersParallel(items, (item) => {
			let all_keys = Object.keys(cov_obj);
			let covariates_map = {};
			let format_year = item.year > 2023 ? 2023 : item.year;
			
			for (let i = 0; i < all_keys.length; i++) {
				let k = all_keys[i];
				let info = cov_obj[k](format_year);
				covariates_map[k] = info;
			}
			
			return {
				covariates_map: covariates_map,
				model_obj: item.model_path,
				options: {
					format: "float32",
					output_mode: "probabilities"
				},
				output_file_path: item.out_base
			};
		}, {
			concurrency: options.concurrency,
			name: "Professions Multinomial Logit Raster Generation"
		});
	}
	
	/**
	 * Clamps probabilties cleanly to rigid LFPR models establishing absolute populations + percent distributions.
	 * Calculates and derives global 'Total (Net)' values synthetically.
	 */
	static async E_clampToPercentagesAndAggregates (arg0_options) {
		let options = (arg0_options) ? arg0_options : {};
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;

		if (!fs.existsSync(this.output_percentages)) fs.mkdirSync(this.output_percentages, { recursive: true });
		if (!fs.existsSync(this.output_aggregates)) fs.mkdirSync(this.output_aggregates, { recursive: true });
		
		let years = landuse_HYDE.sorted_hyde_years;
		
		for (let y = 0; y < years.length; y++) {
			let year = years[y];
			let all_exist = true;
			
			for (let j = 0; j < ["m", "f", "t"].length; j++) {
				for (let i = 0; i < this.categories.length; i++) {
					if (!fs.existsSync(`${this.output_aggregates}${this.categories[i]}_${["m", "f", "t"][j]}_${year}.png`)) all_exist = false;
				}
			}
			if (!overwrite && all_exist) continue;
			
			let pop_t = null;
			let agg_t = {};
			for (let i = 0; i < this.categories.length; i++) agg_t[this.categories[i]] = null;
			let width = 4320, height = 2160;
			
			for (let s = 0; s < this.sexes.length; s++) {
				let sex = this.sexes[s];
				let lfpr_path = `${LFPR_OLS.output_lfpr_rates}lfpr_${sex}_${year}.png`;
				
				if (!fs.existsSync(lfpr_path)) continue;
				let lfpr_raster = GeoPNG.loadNumberRasterImage(lfpr_path, { format: "float32" });
				
				width = lfpr_raster.width;
				height = lfpr_raster.height;
				
				let data_len = lfpr_raster.data.length;
				let pop_raster = new Float32Array(data_len);
				
				// Reconstruct working pool strictly matching 15-80 demographics
				for (let i = 0; i < this.working_cohorts.length; i++) {
					let cp = `${global.age_sex.output_rasters}${sex}_${this.working_cohorts[i]}_${year}.png`;
					if (fs.existsSync(cp)) {
						let c_raster = GeoPNG.loadNumberRasterImage(cp, { format: "float32" });
						for (let j = 0; j < data_len; j++) {
							let val = c_raster.data[j];
							if (!isNaN(val) && val > 0) pop_raster[j] += val;
						}
					}
				}
				
				if (!pop_t) pop_t = new Float32Array(data_len);
				for (let i = 0; i < data_len; i++) pop_t[i] += pop_raster[i];
				
				let prob_rasters = {};
				let missing_probs = false;
				
				// Only load active labor classes (MNL no longer models `not_in_work`)
				for (let i = 0; i < this.olivetti_categories.length; i++) {
					let path = `${this.intermediate_logit_rasters}logit_${sex}_${year}_class_${this.olivetti_categories[i]}.png`;
					if (!fs.existsSync(path)) { missing_probs = true; break; }
					prob_rasters[this.olivetti_categories[i]] = GeoPNG.loadNumberRasterImage(path, { format: "float32" });
				}
				
				if (missing_probs) continue;
				
				// Normalize internal distribution explicitly bounding logic safely to LFPR anchors
				let prob_sum_working = new Float32Array(data_len);
				for (let i = 0; i < this.olivetti_categories.length; i++) {
					let data = prob_rasters[this.olivetti_categories[i]].data;
					for (let j = 0; j < data_len; j++) {
						let val = data[j];
						if (!isNaN(val) && val > 0) prob_sum_working[j] += val;
					}
				}
				
				for (let i = 0; i < this.categories.length; i++) {
					let c = this.categories[i];
					if (!agg_t[c]) agg_t[c] = new Float32Array(data_len);
					
					let pct_arr = new Float32Array(data_len);
					let agg_arr = new Float32Array(data_len);
					let prob_data = prob_rasters[c] ? prob_rasters[c].data : null;
					
					for (let j = 0; j < data_len; j++) {
						let pop = pop_raster[j];
						if (pop <= 0) continue;
						
						let lfpr = lfpr_raster.data[j];
						if (isNaN(lfpr)) lfpr = 0;
						
						let final_pct = 0;
						if (c === "not_in_work") {
							final_pct = Math.max(0, 1.0 - lfpr);
						} else {
							let sum_w = prob_sum_working[j];
							let p_val = prob_data[j];
							if (isNaN(p_val) || p_val < 0) p_val = 0;
							
							if (sum_w <= 0) {
								final_pct = lfpr / this.olivetti_categories.length; // Hard fallback evenly distributes unknown sectors 
							} else {
								final_pct = lfpr * (p_val / sum_w);
							}
						}
						
						pct_arr[j] = final_pct;
						agg_arr[j] = final_pct * pop;
						agg_t[c][j] += agg_arr[j];
					}
					
					GeoPNG.saveNumberRasterImage({
						file_path: `${this.output_percentages}${c}_${sex}_${year}.png`,
						format: "float32",
						width: width, height: height,
						function: (idx) => pct_arr[idx]
					});
					
					GeoPNG.saveNumberRasterImage({
						file_path: `${this.output_aggregates}${c}_${sex}_${year}.png`,
						format: "float32",
						width: width, height: height,
						function: (idx) => agg_arr[idx]
					});
				}
			}
			
			// Net Total Synthesiser via weighted aggregation 
			if (pop_t) {
				for (let i = 0; i < this.categories.length; i++) {
					let c = this.categories[i];
					
					GeoPNG.saveNumberRasterImage({
						file_path: `${this.output_percentages}${c}_t_${year}.png`,
						format: "float32",
						width: width, height: height,
						function: (idx) => {
							let total_p = pop_t[idx];
							if (total_p <= 0) return 0;
							return agg_t[c][idx] / total_p;
						}
					});
					
					GeoPNG.saveNumberRasterImage({
						file_path: `${this.output_aggregates}${c}_t_${year}.png`,
						format: "float32",
						width: width, height: height,
						function: (idx) => agg_t[c][idx]
					});
				}
				console.log(`Clamped Percentages & Absolute Aggregates mapped securely for m, f, t in year ${year}.`);
			}
			
			await Blacktraffic.yield();
		}
	}
	
	static async processRasters (arg0_options) {
		let options = (arg0_options) ? arg0_options : {};
		if (!options.exclude) options.exclude = [];
		if (options.skip_training || options.use_existing_models || options.train === false) {
			if (!options.exclude.includes("B")) options.exclude.push("B");
			if (!options.exclude.includes("C")) options.exclude.push("C");
			console.log(`[professions] Skipping Steps B & C training (using existing models).`);
		}
		
		if (!options.exclude.includes("A")) await this.A_standardiseTargets(options);
		if (!options.exclude.includes("B")) await this.B_trainMultinomialLogitModels(options);
		if (!options.exclude.includes("C")) await this.C_mergeMultinomialLogitModels(options);
		if (!options.exclude.includes("D")) await this.D_generateMultinomialLogitRasters(options);
		if (!options.exclude.includes("E")) await this.E_clampToPercentagesAndAggregates(options);
	}
};