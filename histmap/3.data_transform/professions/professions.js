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
		return await GeoPNG.processTimeseriesParallel({
			concurrency: options.concurrency,
			items: items,
			name: "Professions ALR Model Training",
			task_generator: (item) => {
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
					type: "train_alr_model",
					categories: this.olivetti_categories,
					covariates_map: covariates_map,
					model_path: model_path,
					reference_category: "agriculture",
					options: {
						fit_intercept: false,
						lambda: Math.returnSafeNumber(options.lambda, 1e-3)
					},
					target_paths: target_paths
				};
			},
			handler: async (item) => {
				let all_keys = Object.keys(cov_obj);
				let covariates_map = {};
				let format_year = item.year > 2023 ? 2023 : item.year;
				let model_path = `${this.intermediate_logit_folder}multinomial_model_${item.sex}_${item.year}.json`;
				
				for (let i = 0; i < all_keys.length; i++)
					covariates_map[all_keys[i]] = cov_obj[all_keys[i]](format_year);
				
				let { rasters_obj, valid_keys } = Statistics.loadCovariateRasters(covariates_map);
				let target_rasters = {};
				for (let i = 0; i < this.olivetti_categories.length; i++) {
					let cat = this.olivetti_categories[i];
					let tp = `${this.standardised_targets_folder}global_${cat}_${item.sex}_${item.year}.png`;
					if (!fs.existsSync(tp)) return null;
					target_rasters[cat] = GeoPNG.loadNumberRasterImage(tp, { format: "float32" });
				}
				
				let data_len = target_rasters[this.olivetti_categories[0]].data.length;
				let X = [];
				let Y = [];
				for (let i = 0; i < data_len; i++) {
					let cat_pops = [];
					let total_pop = 0;
					for (let j = 0; j < this.olivetti_categories.length; j++) {
						let cp = target_rasters[this.olivetti_categories[j]].data[i];
						cp = (isNaN(cp) || cp < 0) ? 0 : cp;
						cat_pops.push(cp);
						total_pop += cp;
					}
					if (total_pop <= 0) continue;
					
					let is_valid = true;
					let x_row = [];
					for (let j = 0; j < valid_keys.length; j++) {
						let val = rasters_obj[valid_keys[j]].data[i];
						if (isNaN(val)) { is_valid = false; break; }
						x_row.push(val);
					}
					if (!is_valid) continue;
					
					let prop_row = new Float32Array(this.olivetti_categories.length);
					let inv_tot = 1/total_pop;
					for (let j = 0; j < this.olivetti_categories.length; j++)
						prop_row[j] = cat_pops[j]*inv_tot;
					X.push(x_row);
					Y.push(prop_row);
				}
				if (X.length === 0) return null;
				
				return await Statistics.trainALRModel(model_path, {
					categories: this.olivetti_categories,
					keys: valid_keys,
					reference_category: "agriculture",
					X: X,
					Y: Y
				}, {
					fit_intercept: false,
					lambda: Math.returnSafeNumber(options.lambda, 1e-3)
				});
			}
		});
	}
	
	/**
	 * Builds epoch-aware historical models (Pre-Industrial, Industrial, Modern) as well as
	 * a global geomean fallback to respect structural economic transformations across centuries.
	 */
	static async C_mergeMultinomialLogitModels (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;

		//Declare local instance variables
		let train_years = landuse_HYDE.sorted_hyde_years.filter(y => y >= 1750 && y <= 2025);
		
		for (let s = 0; s < this.sexes.length; s++) {
			let sex = this.sexes[s];
			let ensemble_models = [];
			let max_samples = 1;
			let models_loaded = 0;
			let raw_models = [];
			let unified_path = `${this.intermediate_logit_folder}multinomial_model_unified_${sex}.json`;
			let weights_path = `${this.intermediate_logit_folder}anchor_coverage_weights_${sex}.json`;

			if (!overwrite && fs.existsSync(unified_path)) {
				console.log(`Unified Multinomial Logit model for sex (${sex}) already exists. Skipping merge.`);
				continue;
			}
			
			for (let y = 0; y < train_years.length; y++) {
				let year = train_years[y];
				let p = `${this.intermediate_logit_folder}multinomial_model_${sex}_${year}.json`;
				
				if (fs.existsSync(p)) {
					let m = JSON.parse(fs.readFileSync(p, "utf8"));
					let samples = Math.returnSafeNumber(m.training?.sample_count, 1000);
					if (samples > max_samples) max_samples = samples;
					
					raw_models.push({
						model_path: p,
						sample_count: samples,
						year: year
					});
					models_loaded++;
				}
			}
			
			if (models_loaded === 0) continue;
			
			let total_coverage_weight = 0;
			for (let i = 0; i < raw_models.length; i++) {
				let entry = raw_models[i];
				let coverage_metric = Math.pow(entry.sample_count/max_samples, 0.3);
				entry.coverage = coverage_metric;
				total_coverage_weight += coverage_metric;
			}
			
			for (let i = 0; i < raw_models.length; i++) {
				let entry = raw_models[i];
				let norm_w = (total_coverage_weight > 0) ? (entry.coverage/total_coverage_weight) : (1/raw_models.length);
				ensemble_models.push({
					coverage: entry.coverage,
					model: entry.model_path,
					sample_count: entry.sample_count,
					weight: norm_w,
					year: entry.year
				});
			}
			
			let unified_model = {
				categories: this.olivetti_categories,
				models: ensemble_models,
				sample_count_max: max_samples,
				total_anchors: models_loaded,
				type: "multinomial_ensemble"
			};
			
			fs.writeFileSync(unified_path, JSON.stringify(unified_model, null, 2));
			fs.writeFileSync(weights_path, JSON.stringify(ensemble_models, null, 2));
			console.log(`Unified coverage-weighted MNL ensemble generated for sex (${sex}) using ${models_loaded} anchors.`);
		}
	}
	
	/**
	 * Generates theoretical percent distributions across all temporal horizons using epoch-aware models.
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
			
			for (let y = 0; y < years.length; y++) {
				let year = years[y];
				let out_base = `${this.intermediate_logit_rasters}logit_${sex}_${year}.png`;
				let check_path = out_base.replace(".png", `_class_${this.olivetti_categories[0]}.png`);
				if (!overwrite && fs.existsSync(check_path)) continue;
				
				let model_path = `${this.intermediate_logit_folder}multinomial_model_${sex}_${year}.json`;
				let unified_path = `${this.intermediate_logit_folder}multinomial_model_unified_${sex}.json`;
				let has_local_anchor = fs.existsSync(model_path);
				let resolved_model = model_path;

				if (fs.existsSync(unified_path)) {
					let unified_data = JSON.parse(fs.readFileSync(unified_path, "utf8"));
					
					if (unified_data.type === "multinomial_ensemble" && Array.isArray(unified_data.models)) {
						let dynamic_models = [];
						let total_w = 0;
						
						for (let m = 0; m < unified_data.models.length; m++) {
							let entry = unified_data.models[m];
							let anchor_year = entry.year || 1950;
							let dt = Math.abs(year - anchor_year);
							let kernel = Math.exp(-dt/50);
							let w = (entry.weight || 1)*kernel;
							dynamic_models.push({ model: entry.model, weight: w, year: anchor_year });
							total_w += w;
						}
						
						if (total_w > 0) {
							for (let m = 0; m < dynamic_models.length; m++)
								dynamic_models[m].weight /= total_w;
						}
						
						if (has_local_anchor) {
							let local_idx = dynamic_models.findIndex(m => m.model === model_path);
							for (let m = 0; m < dynamic_models.length; m++)
								dynamic_models[m].weight *= 0.8;
							if (local_idx !== -1) {
								dynamic_models[local_idx].weight += 0.2;
							} else {
								dynamic_models.push({ model: model_path, weight: 0.2, year: year });
							}
						}
						
						resolved_model = {
							categories: this.olivetti_categories,
							models: dynamic_models,
							target_year: year,
							type: "multinomial_ensemble"
						};
					} else {
						resolved_model = has_local_anchor ? model_path : unified_path;
					}
				} else if (!has_local_anchor) {
					resolved_model = null;
				}

				if (resolved_model)
					items.push({ model_obj: resolved_model, out_base: out_base, sex: sex, year: year });
			}
		}
		
		if (items.length === 0) return [];
		
		//Return statement
		return await GeoPNG.processTimeseriesParallel({
			concurrency: options.concurrency,
			items: items,
			name: "Professions ALR Raster Generation",
			task_generator: (item) => {
				let all_keys = Object.keys(cov_obj);
				let covariates_map = {};
				let format_year = item.year > 2023 ? 2023 : item.year;
				
				for (let i = 0; i < all_keys.length; i++) {
					let k = all_keys[i];
					let info = cov_obj[k](format_year);
					covariates_map[k] = info;
				}
				
				return {
					type: "generate_alr_raster",
					covariates_map: covariates_map,
					model_obj: item.model_obj,
					options: {
						format: "float32",
						mask_uninhabited: true
					},
					output_file_path: item.out_base
				};
			},
			handler: async (item) => {
				let all_keys = Object.keys(cov_obj);
				let covariates_map = {};
				let format_year = item.year > 2023 ? 2023 : item.year;
				for (let i = 0; i < all_keys.length; i++)
					covariates_map[all_keys[i]] = cov_obj[all_keys[i]](format_year);
				
				await Statistics.generateALRRaster(item.out_base, {
					covariates_obj: covariates_map,
					model_obj: item.model_obj
				});
			}
		});
	}
	
	/**
	 * Clamps probabilties cleanly to rigid LFPR models establishing absolute populations + percent distributions.
	 * Calculates and derives global 'Total (Net)' values synthetically.
	 */
	static async E_clampToPercentagesAndAggregates (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};

		//Declare local instance variables
		let categories = this.categories;
		let olivetti_categories = this.olivetti_categories;
		let output_aggregates = this.output_aggregates;
		let output_percentages = this.output_percentages;
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
		let sexes = this.sexes;
		let working_cohorts = this.working_cohorts;
		let years = landuse_HYDE.sorted_hyde_years;

		if (!fs.existsSync(output_percentages)) fs.mkdirSync(output_percentages, { recursive: true });
		if (!fs.existsSync(output_aggregates)) fs.mkdirSync(output_aggregates, { recursive: true });

		let target_years = years.filter((year) => {
			if (overwrite) return true;
			for (let j = 0; j < ["m", "f", "t"].length; j++) {
				for (let i = 0; i < categories.length; i++) {
					if (!fs.existsSync(`${output_aggregates}${categories[i]}_${["m", "f", "t"][j]}_${year}.png`)) return true;
				}
			}
			return false;
		});

		if (target_years.length === 0) return [];

		//Return statement
		return await GeoPNG.processTimeseriesParallel({
			concurrency: options.concurrency || 8,
			items: target_years,
			name: "Professions E_clampToPercentagesAndAggregates",
			task_generator: (year) => {
				return {
					type: "clamp_professions",
					age_sex_folder: global.age_sex.output_rasters,
					categories: categories,
					lfpr_folder: LFPR_OLS.output_lfpr_rates,
					logit_rasters_folder: this.intermediate_logit_rasters,
					olivetti_categories: olivetti_categories,
					output_aggregates: output_aggregates,
					output_percentages: output_percentages,
					sexes: sexes,
					working_cohorts: working_cohorts,
					year: year
				};
			},
			handler: async (year) => {
				let agg_t = {};
				for (let i = 0; i < categories.length; i++) agg_t[categories[i]] = null;
				let height = 2160;
				let pop_t = null;
				let width = 4320;

				for (let s = 0; s < sexes.length; s++) {
					let sex = sexes[s];
					let lfpr_path = `${LFPR_OLS.output_lfpr_rates}lfpr_${sex}_${year}.png`;
					
					if (!fs.existsSync(lfpr_path)) continue;
					let lfpr_raster = GeoPNG.loadNumberRasterImage(lfpr_path, { format: "float32" });
					
					width = lfpr_raster.width;
					height = lfpr_raster.height;
					
					let data_len = lfpr_raster.data.length;
					let pop_raster = new Float32Array(data_len);
					
					for (let i = 0; i < working_cohorts.length; i++) {
						let cp = `${global.age_sex.output_rasters}${sex}_${working_cohorts[i]}_${year}.png`;
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
					
					for (let i = 0; i < olivetti_categories.length; i++) {
						let path = `${this.intermediate_logit_rasters}logit_${sex}_${year}_class_${olivetti_categories[i]}.png`;
						if (!fs.existsSync(path)) { missing_probs = true; break; }
						prob_rasters[olivetti_categories[i]] = GeoPNG.loadNumberRasterImage(path, { format: "float32" });
					}
					
					if (missing_probs) continue;
					
					let prob_sum_working = new Float32Array(data_len);
					for (let i = 0; i < olivetti_categories.length; i++) {
						let data = prob_rasters[olivetti_categories[i]].data;
						for (let j = 0; j < data_len; j++) {
							let val = data[j];
							if (!isNaN(val) && val > 0) prob_sum_working[j] += val;
						}
					}
					
					for (let i = 0; i < categories.length; i++) {
						let c = categories[i];
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
									final_pct = lfpr / olivetti_categories.length;
								} else {
									final_pct = lfpr * (p_val / sum_w);
								}
							}
							
							pct_arr[j] = final_pct;
							agg_arr[j] = final_pct * pop;
							agg_t[c][j] += agg_arr[j];
						}
						
						GeoPNG.saveNumberRasterImage({
							file_path: `${output_percentages}${c}_${sex}_${year}.png`,
							format: "float32",
							height: height,
							width: width,
							function: (idx) => pct_arr[idx]
						});
						
						GeoPNG.saveNumberRasterImage({
							file_path: `${output_aggregates}${c}_${sex}_${year}.png`,
							format: "float32",
							height: height,
							width: width,
							function: (idx) => agg_arr[idx]
						});
					}
				}
				
				if (pop_t) {
					for (let i = 0; i < categories.length; i++) {
						let c = categories[i];
						
						GeoPNG.saveNumberRasterImage({
							file_path: `${output_percentages}${c}_t_${year}.png`,
							format: "float32",
							height: height,
							width: width,
							function: (idx) => {
								let total_p = pop_t[idx];
								if (total_p <= 0) return 0;
								return agg_t[c][idx] / total_p;
							}
						});
						
						GeoPNG.saveNumberRasterImage({
							file_path: `${output_aggregates}${c}_t_${year}.png`,
							format: "float32",
							height: height,
							width: width,
							function: (idx) => agg_t[c][idx]
						});
					}
				}
			}
		});
	}
	
	static async processRasters (arg0_options) {
		let options = (arg0_options) ? arg0_options : {};
		if (!options.exclude) options.exclude = [];
		let skip_primary = (options.skip_primary || options.skip_raw || options.skip_primary_data || options.skip_raw_data || options.skip_databases);
		let skip_training = (options.skip_training || options.use_existing_models || options.train === false);
		
		if (skip_training || skip_primary) {
			if (!options.exclude.includes("A")) options.exclude.push("A");
		}
		if (skip_training) {
			if (!options.exclude.includes("B")) options.exclude.push("B");
			if (!options.exclude.includes("C")) options.exclude.push("C");
			console.log(`[professions] Skipping Steps A, B & C training (using existing models).`);
		}
		
		if (!options.exclude.includes("A")) await this.A_standardiseTargets(options);
		if (!options.exclude.includes("B")) await this.B_trainMultinomialLogitModels(options);
		if (!options.exclude.includes("C")) await this.C_mergeMultinomialLogitModels(options);
		if (!options.exclude.includes("D")) await this.D_generateMultinomialLogitRasters(options);
		if (!options.exclude.includes("E")) await this.E_clampToPercentagesAndAggregates(options);
	}
};