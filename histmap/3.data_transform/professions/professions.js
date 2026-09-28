global.professions = class {
	static cf = `${h3}/professions/`;
	static covariates_obj = () => {
		let return_obj = {
			...age_sex.covariates_obj,
			"lfpr_f": (y) => [`${LFPR_OLS.output_lfpr_rates}lfpr_f_${y}.png`, "float32"],
			"lfpr_m": (y) => [`${LFPR_OLS.output_lfpr_rates}lfpr_m_${y}.png`, "float32"]
		};

		//Return statement
		delete return_obj.gini;
		return return_obj;
	};
	
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
				for (let i = 0; i < this.categories.length; i++)
					if (!fs.existsSync(`${this.standardised_targets_folder}global_${this.categories[i]}_${sex}_${year}.png`)) all_exist = false;
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
								return pop * Math.max(0, (1.0 - (isNaN(lfpr) ? 0 : lfpr)));
							} else {
								let rate = olivetti_rasters[c].data[idx];
								return pop * (isNaN(rate) ? 0 : rate);
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
	static async B_trainIndependentEnsembles (arg0_options) {
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
				let all_targets_exist = true;
				for (let c = 0; c < this.olivetti_categories.length; c++) {
					let cat = this.olivetti_categories[c];
					if (!fs.existsSync(`${this.standardised_targets_folder}global_${cat}_${sex}_${year}.png`)) {
						all_targets_exist = false;
						break;
					}
				}
				if (!all_targets_exist) continue;
				
				for (let c = 0; c < this.olivetti_categories.length; c++) {
					let cat = this.olivetti_categories[c];
					let model_path = `${this.intermediate_logit_folder}ensemble_model_${cat}_${sex}_${year}.json`;
					if (overwrite || !fs.existsSync(model_path))
						items.push({ cat: cat, sex: sex, year: year });
				}
			}
		}
		
		if (items.length === 0) return [];
		
		//Return statement
		return await GeoPNG.processTimeseriesParallel({
			concurrency: options.concurrency,
			items: items,
			name: "Professions Superlearner Model Training",
			task_generator: (item) => {
				let all_keys = Object.keys(cov_obj);
				let covariates_map = {};
				let format_year = item.year > 2023 ? 2023 : item.year;
				let model_path = `${this.intermediate_logit_folder}ensemble_model_${item.cat}_${item.sex}_${item.year}.json`;
				let target_paths = {};
				for (let i = 0; i < all_keys.length; i++) covariates_map[all_keys[i]] = cov_obj[all_keys[i]](format_year);
				for (let i = 0; i < this.olivetti_categories.length; i++) {
					let c = this.olivetti_categories[i];
					target_paths[c] = `${this.standardised_targets_folder}global_${c}_${item.sex}_${item.year}.png`;
				}
				
				return {
					type: "train_superlearner_model",
					cat: item.cat,
					categories: this.olivetti_categories,
					covariates_map: covariates_map,
					model_path: model_path,
					options: { fit_intercept: true, lambda: Math.returnSafeNumber(options.lambda, 1e-4) },
					target_paths: target_paths
				};
			},
			handler: async (item) => {
				let all_keys = Object.keys(cov_obj);
				let covariates_map = {};
				let format_year = item.year > 2023 ? 2023 : item.year;
				let model_path = `${this.intermediate_logit_folder}ensemble_model_${item.cat}_${item.sex}_${item.year}.json`;
				
				for (let i = 0; i < all_keys.length; i++)
					covariates_map[all_keys[i]] = cov_obj[all_keys[i]](format_year);
				
				let { rasters_obj, valid_keys } = Statistics.loadCovariateRasters(covariates_map);
				let target_rasters = {};
				for (let i = 0; i < this.olivetti_categories.length; i++) {
					let c = this.olivetti_categories[i];
					let tp = `${this.standardised_targets_folder}global_${c}_${item.sex}_${item.year}.png`;
					if (!fs.existsSync(tp)) return null;
					target_rasters[c] = GeoPNG.loadNumberRasterImage(tp, { format: "float32" });
				}
				
				let data_len = target_rasters[this.olivetti_categories[0]].data.length;
				let X = [];
				let Y = [];
				for (let i = 0; i < data_len; i++) {
					let cat_pops = [];
					let total_pop = 0;
					let this_cat_pop = target_rasters[item.cat].data[i];
					this_cat_pop = (isNaN(this_cat_pop) || this_cat_pop < 0) ? 0 : this_cat_pop;
					
					for (let j = 0; j < this.olivetti_categories.length; j++) {
						let cp = target_rasters[this.olivetti_categories[j]].data[i];
						cp = (isNaN(cp) || cp < 0) ? 0 : cp;
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
					
					let p = this_cat_pop / total_pop;
					p = Math.max(0.001, Math.min(0.999, p));
					let logit = Math.log(p / (1 - p));
					
					X.push(x_row);
					Y.push(logit);
				}
				if (X.length === 0) return null;
				
				let max_samples = 5000;
				if (X.length > max_samples) {
					let sampled_X = [];
					let sampled_Y = [];
					let step = X.length / max_samples;
					for (let i = 0; i < max_samples; i++) {
						let idx = Math.floor(i * step + Math.random() * step);
						if (idx >= X.length) idx = X.length - 1;
						sampled_X.push(X[idx]);
						sampled_Y.push(Y[idx]);
					}
					X = sampled_X;
					Y = sampled_Y;
				}
				
				return await Statistics.trainSuperlearner(model_path, {
					keys: valid_keys,
					X: X,
					Y: Y
				}, {
					linear_options: { fit_intercept: true, lambda: Math.returnSafeNumber(options.lambda, 1e-4) },
					rf_options: { max_depth: 8, min_samples_split: 5, n_trees: 15 }
				});
			}
		});
	}
	
	/**
	 * Builds epoch-aware historical models (Pre-Industrial, Industrial, Modern) as well as
	 * a global geomean fallback to respect structural economic transformations across centuries.
	 */
	static async C_mergeHistoricalEnsembles (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;

		//Declare local instance variables
		let train_years = landuse_HYDE.sorted_hyde_years.filter(y => y >= 1750 && y <= 2025);
		
		for (let s = 0; s < this.sexes.length; s++) {
			let sex = this.sexes[s];
			for (let c = 0; c < this.olivetti_categories.length; c++) {
				let cat = this.olivetti_categories[c];
				let ensemble_models = [];
				let max_samples = 1;
				let models_loaded = 0;
				let raw_models = [];
				let unified_path = `${this.intermediate_logit_folder}ensemble_model_unified_${cat}_${sex}.json`;
				let weights_path = `${this.intermediate_logit_folder}anchor_coverage_weights_${cat}_${sex}.json`;

				if (!overwrite && fs.existsSync(unified_path)) {
					console.log(`Unified Superlearner ensemble for sex (${sex}), category (${cat}) already exists. Skipping merge.`);
					continue;
				}
				
				for (let y = 0; y < train_years.length; y++) {
					let year = train_years[y];
					let p = `${this.intermediate_logit_folder}ensemble_model_${cat}_${sex}_${year}.json`;
					if (fs.existsSync(p)) {
						let m = JSON.parse(fs.readFileSync(p, "utf8"));
						let samples = m.sample_count || m.metrics?.sample_count || 1000;
						if (samples > max_samples) max_samples = samples;
						raw_models.push({ model_path: p, sample_count: samples, year: year });
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
					cat: cat,
					models: ensemble_models,
					sample_count_max: max_samples,
					total_anchors: models_loaded,
					type: "superlearner_ensemble"
				};
				
				fs.writeFileSync(unified_path, JSON.stringify(unified_model, null, 2));
				fs.writeFileSync(weights_path, JSON.stringify(ensemble_models, null, 2));
				console.log(`Unified coverage-weighted Superlearner ensemble generated for sex (${sex}), category (${cat}) using ${models_loaded} anchors.`);
			}
		}
	}
	
	/**
	 * Generates theoretical percent distributions across all temporal horizons using epoch-aware models.
	 */
	static async D_generateEnsembleRasters (arg0_options) {
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
				
				let resolved_models = {};
				
				for (let c = 0; c < this.olivetti_categories.length; c++) {
					let cat = this.olivetti_categories[c];
					let model_path = `${this.intermediate_logit_folder}ensemble_model_${cat}_${sex}_${year}.json`;
					let unified_path = `${this.intermediate_logit_folder}ensemble_model_unified_${cat}_${sex}.json`;
					let has_local_anchor = fs.existsSync(model_path);
					let resolved_model = model_path;

					if (fs.existsSync(unified_path)) {
						let unified_data = JSON.parse(fs.readFileSync(unified_path, "utf8"));
						
						if (unified_data.type === "superlearner_ensemble" && Array.isArray(unified_data.models)) {
							let dynamic_models = [];
							let effective_year = Math.max(1890, Math.min(2025, year));
							let total_w = 0;
							
							for (let m = 0; m < unified_data.models.length; m++) {
								let entry = unified_data.models[m];
								let anchor_year = entry.year || 1950;
								let dt = Math.abs(effective_year - anchor_year);
								let kernel = Math.exp(-dt / 50);
								let w = (entry.weight || 1) * kernel;
								dynamic_models.push({ model: entry.model, weight: w, year: anchor_year });
								total_w += w;
							}
							
							if (total_w > 0)
								for (let m = 0; m < dynamic_models.length; m++) dynamic_models[m].weight /= total_w;
							
							if (has_local_anchor) {
								let local_idx = dynamic_models.findIndex(m => m.model === model_path);
								for (let m = 0; m < dynamic_models.length; m++) dynamic_models[m].weight *= 0.8;
								if (local_idx !== -1) {
									dynamic_models[local_idx].weight += 0.2;
								} else {
									dynamic_models.push({ model: model_path, weight: 0.2, year: year });
								}
							}
							
							resolved_model = {
								cat: cat,
								models: dynamic_models,
								target_year: year,
								type: "superlearner_ensemble"
							};
						} else {
							resolved_model = has_local_anchor ? model_path : unified_path;
						}
					} else if (!has_local_anchor) {
						resolved_model = null;
					}
					
					if (resolved_model) resolved_models[cat] = resolved_model;
				}

				if (Object.keys(resolved_models).length === this.olivetti_categories.length)
					items.push({ resolved_models: resolved_models, out_base: out_base, sex: sex, year: year });
			}
		}
		
		if (items.length === 0) return [];
		
		//Return statement
		return await GeoPNG.processTimeseriesParallel({
			concurrency: options.concurrency,
			items: items,
			name: "Professions Superlearner Raster Generation",
			task_generator: (item) => {
				let all_keys = Object.keys(cov_obj);
				let covariates_map = {};
				let format_year = item.year > 2023 ? 2023 : item.year;
				for (let i = 0; i < all_keys.length; i++) covariates_map[all_keys[i]] = cov_obj[all_keys[i]](format_year);
				
				return {
					type: "generate_superlearner_raster",
					covariates_map: covariates_map,
					options: { format: "float32", mask_uninhabited: true },
					output_file_path: item.out_base,
					resolved_models: item.resolved_models,
					sex: item.sex,
					year: item.year
				};
			},
			handler: async (item) => {
				let all_keys = Object.keys(cov_obj);
				let covariates_map = {};
				let format_year = item.year > 2023 ? 2023 : item.year;
				for (let i = 0; i < all_keys.length; i++)
					covariates_map[all_keys[i]] = cov_obj[all_keys[i]](format_year);
				
				let { rasters_obj, valid_keys } = Statistics.loadCovariateRasters(covariates_map);
				
				let data_len = rasters_obj[valid_keys[0]].data.length;
				let width = rasters_obj[valid_keys[0]].width;
				let height = rasters_obj[valid_keys[0]].height;
				let output_arrays = {};
				
				let num_valid_keys = valid_keys.length;
				let feature_arrays = [];
				for (let j = 0; j < num_valid_keys; j++) {
					feature_arrays.push(rasters_obj[valid_keys[j]].data);
				}
				
				let key_to_valid_idx = {};
				for (let k = 0; k < num_valid_keys; k++) key_to_valid_idx[valid_keys[k]] = k;

				if (!global._superlearner_model_cache) global._superlearner_model_cache = {};
				let model_cache = global._superlearner_model_cache;

				function loadModelCached (p) {
					if (!model_cache[p]) model_cache[p] = JSON.parse(fs.readFileSync(p, "utf8"));
					return model_cache[p];
				}

				function prepareCategoryEnsemble (conf) {
					let all_keys = {}, models_list = [];
					if (conf.type === "superlearner_ensemble") {
						for (let m = 0; m < conf.models.length; m++) {
							let obj = loadModelCached(conf.models[m].model);
							(obj.keys || []).forEach(k => all_keys[k] = true);
							models_list.push({ obj: obj, weight: conf.models[m].weight });
						}
					} else {
						let obj = loadModelCached(conf);
						(obj.keys || []).forEach(k => all_keys[k] = true);
						models_list.push({ obj: obj, weight: 1.0 });
					}
					let u_keys = Object.keys(all_keys), n_f = u_keys.length;
					let f_valid = new Int32Array(n_f);
					for (let k = 0; k < n_f; k++) f_valid[k] = (key_to_valid_idx[u_keys[k]] !== undefined) ? key_to_valid_idx[u_keys[k]] : -1;
					let lin_inter = 0, lin_coeffs = new Float64Array(n_f);
					for (let m = 0; m < models_list.length; m++) {
						let entry = models_list[m], obj = entry.obj, W = entry.weight;
						let w_l = (obj.weights && obj.weights.linear !== undefined) ? obj.weights.linear : 0.5;
						lin_inter += W * w_l * ((obj.linear_model && obj.linear_model.intercept) || 0);
						let c_map = (obj.linear_model && obj.linear_model.coefficients) || {};
						for (let k = 0; k < n_f; k++) {
							let c_val = c_map[u_keys[k]];
							if (typeof c_val === "number" && !isNaN(c_val)) lin_coeffs[k] += W * w_l * c_val;
						}
					}
					let top_rf = [...models_list].sort((a, b) => b.weight - a.weight).slice(0, 12);
					let rf_w_sum = top_rf.reduce((acc, e) => acc + e.weight, 0);
					let flat_trees = [];
					for (let m = 0; m < top_rf.length; m++) {
						let entry = top_rf[m], obj = entry.obj;
						let w_rf = (obj.weights && obj.weights.rf !== undefined) ? obj.weights.rf : 0.5;
						let W_n = (rf_w_sum > 0) ? (entry.weight / rf_w_sum) : (1 / top_rf.length);
						let trees = (obj.rf_model && obj.rf_model.trees) || [];
						if (trees.length > 0) {
							let scale = (W_n * w_rf) / trees.length;
							for (let t = 0; t < trees.length; t++) flat_trees.push({ tree: trees[t], weight: scale });
						}
					}
					return { combined_coeffs: lin_coeffs, combined_intercept: lin_inter, feature_valid_indices: f_valid, flat_trees: flat_trees, num_features: n_f };
				}

				function evaluateCategoryEnsemble (prep, feat_arrs, idx, x_buf) {
					let lin_val = prep.combined_intercept;
					for (let k = 0; k < prep.num_features; k++) {
						let v_idx = prep.feature_valid_indices[k];
						let val = (v_idx >= 0) ? feat_arrs[v_idx][idx] : 0;
						x_buf[k] = val;
						lin_val += val * prep.combined_coeffs[k];
					}
					let rf_val = 0, n_trees = prep.flat_trees.length;
					for (let t = 0; t < n_trees; t++) {
						let node = prep.flat_trees[t].tree;
						while (!node.is_leaf) node = (x_buf[node.feature_index] <= node.threshold) ? node.left : node.right;
						rf_val += node.value * prep.flat_trees[t].weight;
					}
					return lin_val + rf_val;
				}
				
				let num_cats = this.olivetti_categories.length;
				let prepared_categories = {};
				
				for (let i = 0; i < num_cats; i++) {
					let cat = this.olivetti_categories[i];
					output_arrays[cat] = new Float32Array(data_len);
					prepared_categories[cat] = prepareCategoryEnsemble(item.resolved_models[cat]);
				}

				let popd_idx = key_to_valid_idx["popd_"];
				let popc_idx = key_to_valid_idx["popc_"];
				let popd_arr = (popd_idx !== undefined) ? feature_arrays[popd_idx] : null;
				let popc_arr = (popc_idx !== undefined) ? feature_arrays[popc_idx] : null;
				
				let x_buf = new Float64Array(100);
				let p_vals = new Float64Array(num_cats);
				let log_interval = Math.floor(data_len / 10);
				let task_sex = item.sex ? item.sex.toUpperCase() : "";
				let task_year = (item.year !== undefined) ? item.year : "";
				console.log(`[Professions Raster] [${task_sex} ${task_year}] Starting raster computation (${num_valid_keys} covariates, ${prepared_categories[this.olivetti_categories[0]].flat_trees.length} trees/cat)..`);
				
				for (let i = 0; i < data_len; i++) {
					if (i > 0 && i % log_interval === 0) {
						let pct = Math.round((i / data_len) * 100);
						console.log(`[Professions Raster] [${task_sex} ${task_year}] Generating raster: ${pct}% complete..`);
					}

					// Population guard: immediately skip uninhabited cells (ocean/desert/ice)
					let pop = (popd_arr ? popd_arr[i] : 0) || (popc_arr ? popc_arr[i] : 0);
					if (isNaN(pop) || pop <= 0) {
						for (let j = 0; j < num_cats; j++) output_arrays[this.olivetti_categories[j]][i] = 0;
						continue;
					}
					
					let is_valid = true;
					for (let j = 0; j < num_valid_keys; j++) {
						let v = feature_arrays[j][i];
						if (isNaN(v)) { is_valid = false; break; }
					}
					
					if (is_valid) {
						let sum_p = 0;
						
						for (let j = 0; j < num_cats; j++) {
							let cat = this.olivetti_categories[j];
							let logit_val = evaluateCategoryEnsemble(prepared_categories[cat], feature_arrays, i, x_buf);
							let p = Math.exp(logit_val) / (1 + Math.exp(logit_val));
							p_vals[j] = p;
							sum_p += p;
						}
						
						for (let j = 0; j < num_cats; j++) {
							let cat = this.olivetti_categories[j];
							output_arrays[cat][i] = (sum_p > 0) ? (p_vals[j] / sum_p) : 0;
						}
					} else {
						for (let j = 0; j < num_cats; j++) {
							output_arrays[this.olivetti_categories[j]][i] = NaN;
						}
					}
				}
				
				for (let i = 0; i < num_cats; i++) {
					let cat = this.olivetti_categories[i];
					let file_path = item.out_base.replace(".png", `_class_${cat}.png`);
					GeoPNG.saveNumberRasterImage({
						file_path: file_path,
						format: "float32",
						height: height,
						width: width,
						function: (idx) => output_arrays[cat][idx]
					});
				}
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
		let years = (options.years) ? options.years : landuse_HYDE.sorted_hyde_years;

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
				let baselines_by_sex = {
					f: this.getDynamicSectorBaselines(year, "f"),
					m: this.getDynamicSectorBaselines(year, "m")
				};

				return {
					type: "clamp_professions",
					age_sex_folder: global.age_sex.output_rasters,
					categories: categories,
					lfpr_folder: LFPR_OLS.output_lfpr_rates,
					logit_rasters_folder: this.intermediate_logit_rasters,
					olivetti_categories: olivetti_categories,
					output_aggregates: output_aggregates,
					output_percentages: output_percentages,
					sector_baselines: baselines_by_sex,
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
					
					let num_olivetti = olivetti_categories.length;
					let sector_baselines = this.getDynamicSectorBaselines(year, sex);
					let sample = [];
					let tot_sample_pop = 0;
					let step = Math.max(1, Math.floor(data_len / 30000));

					for (let j = 0; j < data_len; j += step) {
						if (pop_raster[j] > 0) {
							sample.push({
								p: pop_raster[j],
								s: [
									prob_rasters[olivetti_categories[0]].data[j] || 0,
									prob_rasters[olivetti_categories[1]].data[j] || 0,
									prob_rasters[olivetti_categories[2]].data[j] || 0,
									prob_rasters[olivetti_categories[3]].data[j] || 0
								]
							});
							tot_sample_pop += pop_raster[j];
						}
					}

					let lambda = new Float64Array(num_olivetti);
					for (let i = 0; i < num_olivetti; i++) {
						let cat = olivetti_categories[i];
						lambda[i] = (sector_baselines && sector_baselines[cat] !== undefined)
							? sector_baselines[cat]
							: 0.25;
					}

					// Fast iterative proportional fitting (IPF) raking on sample to align macro proportions
					if (tot_sample_pop > 0 && sample.length > 0) {
						let q = new Float64Array(num_olivetti);
						for (let iter = 0; iter < 10; iter++) {
							for (let i = 0; i < num_olivetti; i++) q[i] = 0;
							for (let k = 0; k < sample.length; k++) {
								let it = sample[k];
								let sum_ls = lambda[0]*it.s[0] + lambda[1]*it.s[1] + lambda[2]*it.s[2] + lambda[3]*it.s[3];
								if (sum_ls > 0) {
									let w = it.p / sum_ls;
									q[0] += (lambda[0] * it.s[0]) * w;
									q[1] += (lambda[1] * it.s[1]) * w;
									q[2] += (lambda[2] * it.s[2]) * w;
									q[3] += (lambda[3] * it.s[3]) * w;
								}
							}
							let sum_l = 0;
							for (let i = 0; i < num_olivetti; i++) {
								let target_mu = (sector_baselines && sector_baselines[olivetti_categories[i]] !== undefined)
									? sector_baselines[olivetti_categories[i]]
									: 0.25;
								let current_share = q[i] / tot_sample_pop;
								lambda[i] *= (target_mu / Math.max(1e-7, current_share));
								sum_l += lambda[i];
							}
							if (sum_l > 0)
								for (let i = 0; i < num_olivetti; i++) lambda[i] /= sum_l;
						}
					}

					let agg_arrays = {};
					let pct_arrays = {};
					for (let i = 0; i < categories.length; i++) {
						let c = categories[i];
						pct_arrays[c] = new Float32Array(data_len);
						agg_arrays[c] = new Float32Array(data_len);
						if (!agg_t[c]) agg_t[c] = new Float32Array(data_len);
					}

					let l0 = lambda[0], l1 = lambda[1], l2 = lambda[2], l3 = lambda[3];
					let p0 = prob_rasters[olivetti_categories[0]].data, p1 = prob_rasters[olivetti_categories[1]].data;
					let p2 = prob_rasters[olivetti_categories[2]].data, p3 = prob_rasters[olivetti_categories[3]].data;
					let pct_c0 = pct_arrays[olivetti_categories[0]], pct_c1 = pct_arrays[olivetti_categories[1]];
					let pct_c2 = pct_arrays[olivetti_categories[2]], pct_c3 = pct_arrays[olivetti_categories[3]], pct_niw = pct_arrays["not_in_work"];
					let agg_c0 = agg_arrays[olivetti_categories[0]], agg_c1 = agg_arrays[olivetti_categories[1]];
					let agg_c2 = agg_arrays[olivetti_categories[2]], agg_c3 = agg_arrays[olivetti_categories[3]], agg_niw = agg_arrays["not_in_work"];
					let agg_t0 = agg_t[olivetti_categories[0]], agg_t1 = agg_t[olivetti_categories[1]];
					let agg_t2 = agg_t[olivetti_categories[2]], agg_t3 = agg_t[olivetti_categories[3]], agg_t_niw = agg_t["not_in_work"];

					for (let j = 0; j < data_len; j++) {
						let pop = pop_raster[j];
						if (pop <= 0) continue;

						let lfpr = lfpr_raster.data[j];
						if (isNaN(lfpr)) lfpr = 0;

						let s0 = l0 * p0[j], s1 = l1 * p1[j], s2 = l2 * p2[j], s3 = l3 * p3[j];
						let sum_s = s0 + s1 + s2 + s3;

						let norm_s = (sum_s > 0) ? (lfpr / sum_s) : 0, b = (sum_s > 0) ? 0 : (lfpr * 0.25);
						let final_0 = s0*norm_s + b, final_1 = s1*norm_s + b, final_2 = s2*norm_s + b, final_3 = s3*norm_s + b;
						let final_niw = Math.max(0, 1.0 - lfpr);

						pct_c0[j] = final_0; pct_c1[j] = final_1; pct_c2[j] = final_2; pct_c3[j] = final_3;
						pct_niw[j] = final_niw;

						let a0 = final_0 * pop, a1 = final_1 * pop, a2 = final_2 * pop, a3 = final_3 * pop;
						let aniw = final_niw * pop;

						agg_c0[j] = a0; agg_c1[j] = a1; agg_c2[j] = a2; agg_c3[j] = a3; agg_niw[j] = aniw;
						agg_t0[j] += a0; agg_t1[j] += a1; agg_t2[j] += a2; agg_t3[j] += a3; agg_t_niw[j] += aniw;
					}

					for (let i = 0; i < categories.length; i++) {
						let c = categories[i];

						GeoPNG.saveNumberRasterImage({
							file_path: `${output_percentages}${c}_${sex}_${year}.png`,
							format: "float32",
							height: height,
							width: width,
							function: (idx) => pct_arrays[c][idx]
						});
						
						GeoPNG.saveNumberRasterImage({
							file_path: `${output_aggregates}${c}_${sex}_${year}.png`,
							format: "float32",
							height: height,
							width: width,
							function: (idx) => agg_arrays[c][idx]
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

	/**
	 * Computes dynamic historical macro sector target proportions across epochs.
	 * Anchors to empirical proxies: HYDE agricultural land use in deep time, Stadester urbanisation
	 * from 3000BC, pre-industrial transition splines from 1750, and Olivetti/ILO in modern history.
	 * 
	 * @alias professions.getDynamicSectorBaselines
	 * @param {number} arg0_year
	 * @param {string} [arg1_sex="m"]
	 * 
	 * @returns {Object} Object mapping each olivetti category to its target proportion in [0, 1].
	 */
	static getDynamicSectorBaselines (arg0_year, arg1_sex) {
		//Convert from parameters
		let year = parseInt(arg0_year);
		let sex = (arg1_sex || "m").toLowerCase();

		//Declare local instance variables
		let return_obj = { agriculture: 0.74, manufacturing: 0.12, services: 0.10, informal_labour: 0.04 };

		//1. Modern Era (1890 to 2025 AD): Empirical Olivetti and ILO benchmarks
		if (year >= 1890) {
			let milestones = [
				{ y: 1890, m: { agriculture: 0.473, manufacturing: 0.321, services: 0.170, informal_labour: 0.036 }, f: { agriculture: 0.390, manufacturing: 0.271, services: 0.280, informal_labour: 0.059 } },
				{ y: 1950, m: { agriculture: 0.260, manufacturing: 0.380, services: 0.320, informal_labour: 0.040 }, f: { agriculture: 0.200, manufacturing: 0.300, services: 0.450, informal_labour: 0.050 } },
				{ y: 2000, m: { agriculture: 0.120, manufacturing: 0.260, services: 0.580, informal_labour: 0.040 }, f: { agriculture: 0.080, manufacturing: 0.160, services: 0.720, informal_labour: 0.040 } },
				{ y: 2025, m: { agriculture: 0.060, manufacturing: 0.220, services: 0.680, informal_labour: 0.040 }, f: { agriculture: 0.040, manufacturing: 0.120, services: 0.800, informal_labour: 0.040 } }
			];
			let lower = milestones[0], upper = milestones[milestones.length - 1];
			for (let i = 0; i < milestones.length - 1; i++)
				if (year >= milestones[i].y && year <= milestones[i + 1].y) { lower = milestones[i]; upper = milestones[i + 1]; break; }

			let t = (upper.y === lower.y) ? 0 : (year - lower.y) / (upper.y - lower.y);
			let s = t*t*(3 - 2*t);
			return {
				agriculture: (1 - s)*lower[sex].agriculture + s*upper[sex].agriculture,
				manufacturing: (1 - s)*lower[sex].manufacturing + s*upper[sex].manufacturing,
				services: (1 - s)*lower[sex].services + s*upper[sex].services,
				informal_labour: (1 - s)*lower[sex].informal_labour + s*upper[sex].informal_labour
			};
		}

		//2. Industrial Transition (1750 to 1890 AD): Manufacturing surges preceding services
		if (year >= 1750 && year < 1890) {
			let base_1750 = (sex === "f") ? { agriculture: 0.780, manufacturing: 0.080, services: 0.090, informal_labour: 0.050 } : { agriculture: 0.810, manufacturing: 0.070, services: 0.080, informal_labour: 0.040 };
			let base_1890 = (sex === "f") ? { agriculture: 0.390, manufacturing: 0.271, services: 0.280, informal_labour: 0.059 } : { agriculture: 0.473, manufacturing: 0.321, services: 0.170, informal_labour: 0.036 };
			let t = (year - 1750) / (1890 - 1750), s = t*t*(3 - 2*t);
			return {
				agriculture: (1 - s)*base_1750.agriculture + s*base_1890.agriculture,
				manufacturing: (1 - s)*base_1750.manufacturing + s*base_1890.manufacturing,
				services: (1 - s)*base_1750.services + s*base_1890.services,
				informal_labour: (1 - s)*base_1750.informal_labour + s*base_1890.informal_labour
			};
		}

		//3. Mature Agrarian Era (3000 BC to 1750 AD): Urbanisation proxy drives non-agricultural baseline
		if (year >= -3000 && year < 1750) {
			let u_points = [
				{ y: -3000, u: 0.0011 }, { y: -2000, u: 0.0205 }, { y: -1000, u: 0.0164 }, { y: 0, u: 0.0343 },
				{ y: 500, u: 0.0378 }, { y: 1000, u: 0.0453 }, { y: 1500, u: 0.0467 }, { y: 1750, u: 0.0468 }
			];
			let lower = u_points[0], upper = u_points[u_points.length - 1];
			for (let i = 0; i < u_points.length - 1; i++)
				if (year >= u_points[i].y && year <= u_points[i + 1].y) { lower = u_points[i]; upper = u_points[i + 1]; break; }

			let t = (upper.y === lower.y) ? 0 : (year - lower.y) / (upper.y - lower.y);
			let u_rate = (1 - t)*lower.u + t*upper.u;
			let inf = (sex === "f") ? 0.05 : 0.04;
			let mfg = 0.80*u_rate + ((sex === "f") ? 0.03 : 0.02);
			let serv = 1.00*u_rate + ((sex === "f") ? 0.045 : 0.035);
			return {
				agriculture: Math.max(0.60, 1.0 - serv - mfg - inf),
				manufacturing: mfg,
				services: serv,
				informal_labour: inf
			};
		}

		//4. Pre-Neolithic to Neolithic Transition (-10000 to -3000 BC): Land use intensity scales farming vs foraging
		let lambda_points = [
			{ y: -10000, l: 0.00 }, { y: -8000, l: 0.02 }, { y: -6000, l: 0.10 },
			{ y: -4000, l: 0.70 }, { y: -3000, l: 1.00 }
		];
		let lower = lambda_points[0], upper = lambda_points[lambda_points.length - 1];
		for (let i = 0; i < lambda_points.length - 1; i++)
			if (year >= lambda_points[i].y && year <= lambda_points[i + 1].y) { lower = lambda_points[i]; upper = lambda_points[i + 1]; break; }

		let t = (upper.y === lower.y) ? 0 : (year - lower.y) / (upper.y - lower.y);
		let lambda = (1 - t)*lower.l + t*upper.l;
		return {
			agriculture: lambda*0.88,
			manufacturing: (1 - lambda)*0.01 + lambda*((sex === "f") ? 0.03 : 0.02),
			services: (1 - lambda)*0.01 + lambda*((sex === "f") ? 0.045 : 0.035),
			informal_labour: (1 - lambda)*0.98 + lambda*0.04
		};
	}
	
	static async processRasters (arg0_options) {
		let options = (arg0_options) ? arg0_options : {};
		if (!options.exclude) options.exclude = [];
		let skip_primary = (options.skip_primary || options.skip_raw || options.skip_primary_data || options.skip_raw_data || options.skip_databases);
		let skip_training = (options.skip_training || options.use_existing_models || options.train === false);
		if (skip_training || skip_primary) if (!options.exclude.includes("A")) options.exclude.push("A");
		if (skip_training) {
			if (!options.exclude.includes("B")) options.exclude.push("B");
			if (!options.exclude.includes("C")) options.exclude.push("C");
			console.log(`[professions] Skipping Steps A, B & C training (using existing models).`);
		}
		
		if (!options.exclude.includes("A")) await this.A_standardiseTargets(options);
		if (!options.exclude.includes("B")) await this.B_trainIndependentEnsembles(options);
		if (!options.exclude.includes("C")) await this.C_mergeHistoricalEnsembles(options);
		if (!options.exclude.includes("D")) await this.D_generateEnsembleRasters(options);
		if (!options.exclude.includes("E")) await this.E_clampToPercentagesAndAggregates(options);
	}
};