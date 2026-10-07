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
	static working_cohorts = ["15", "20", "25", "30", "35", "40", "45", "50", "55", "60"];
	
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
				
				let has_olivetti = true, olivetti_rasters = {};
				for (let i = 0; i < this.olivetti_categories.length; i++) {
					let p = `${professions_Olivetti.output_rasters}${this.olivetti_categories[i]}_${sex}_${year}.png`;
					if (fs.existsSync(p)) olivetti_rasters[this.olivetti_categories[i]] = GeoPNG.loadNumberRasterImage(p, { format: "float32" });
					else { has_olivetti = false; break; }
				}
				if (!has_olivetti) continue;
				
				let data_len = olivetti_rasters[this.olivetti_categories[0]].data.length, sum_olivetti = 0;
				for (let i = 0; i < data_len; i++)
					for (let j = 0; j < this.olivetti_categories.length; j++) {
						let val = olivetti_rasters[this.olivetti_categories[j]].data[i];
						if (!isNaN(val) && val > 0) sum_olivetti += val;
					}
				
				// Zero Data Quarantine: Delete from original source and seamlessly skip training anchor
				if (sum_olivetti <= 0) {
					console.warn(`[CLEANUP] Stripping utterly empty Olivetti zero-data for ${sex} ${year}`);
					for (let i = 0; i < this.olivetti_categories.length; i++) {
						let p = `${professions_Olivetti.output_rasters}${this.olivetti_categories[i]}_${sex}_${year}.png`;
						if (fs.existsSync(p)) fs.unlinkSync(p);
					}
					continue;
				}
				
				let lfpr_path = `${LFPR_OLS.output_lfpr_rates}lfpr_${sex}_${year}.png`;
				if (!fs.existsSync(lfpr_path)) continue;
				let lfpr_raster = GeoPNG.loadNumberRasterImage(lfpr_path, { format: "float32" });
				
				let pop_raster = new Float32Array(data_len);
				for (let i = 0; i < this.working_cohorts.length; i++) {
					let cp = `${global.age_sex.output_rasters}${sex}_${this.working_cohorts[i]}_${year}.png`;
					if (fs.existsSync(cp)) {
						let c_raster = GeoPNG.loadNumberRasterImage(cp, { format: "float32" });
						for (let j = 0; j < data_len; j++)
							if (!isNaN(c_raster.data[j]) && c_raster.data[j] > 0) pop_raster[j] += c_raster.data[j];
					}
				}
				
				for (let i = 0; i < this.categories.length; i++) {
					let c = this.categories[i];
					let out_path = `${this.standardised_targets_folder}global_${c}_${sex}_${year}.png`;
					GeoPNG.saveNumberRasterImage({
						file_path: out_path, format: "float32", width: lfpr_raster.width, height: lfpr_raster.height,
						function: (idx) => {
							let pop = pop_raster[idx];
							if (pop <= 0) return 0;
							if (c === "not_in_work") return pop * Math.max(0, (1.0 - (isNaN(lfpr_raster.data[idx]) ? 0 : lfpr_raster.data[idx])));
							return pop * (isNaN(olivetti_rasters[c].data[idx]) ? 0 : olivetti_rasters[c].data[idx]);
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
					type: "train_superlearner_model", cat: item.cat, categories: this.olivetti_categories,
					covariates_map: covariates_map, model_path: model_path, target_paths: target_paths,
					options: { fit_intercept: true, lambda: Math.returnSafeNumber(options.lambda, 1e-4) }
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
				let ensemble_models = [], max_samples = 1, models_loaded = 0, raw_models = [];
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
					ensemble_models.push({ coverage: entry.coverage, model: entry.model_path, sample_count: entry.sample_count, weight: norm_w, year: entry.year });
				}
				
				let unified_model = { cat: cat, models: ensemble_models, sample_count_max: max_samples, total_anchors: models_loaded, type: "superlearner_ensemble" };
				
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
		let years = (options.years) ? options.years : landuse_HYDE.sorted_hyde_years;
		
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
								if (year <= 1890 && anchor_year > 1950) continue;
								let dt = Math.abs(effective_year - anchor_year);
								let kernel = Math.exp(-Math.pow(dt / 25, 2));
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
					type: "generate_superlearner_raster", covariates_map: covariates_map, options: { format: "float32", mask_uninhabited: true },
					output_file_path: item.out_base, resolved_models: item.resolved_models, sex: item.sex, year: item.year
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
					let cat = this.olivetti_categories[i], file_path = item.out_base.replace(".png", `_class_${cat}.png`);
					GeoPNG.saveNumberRasterImage({ file_path: file_path, format: "float32", height: height, width: width, function: (idx) => output_arrays[cat][idx] });
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
			for (let j = 0; j < ["m", "f", "t"].length; j++)
				for (let i = 0; i < categories.length; i++)
					if (!fs.existsSync(`${output_aggregates}${categories[i]}_${["m", "f", "t"][j]}_${year}.png`)) return true;
			return false;
		});

		if (target_years.length === 0) return [];

		//Return statement
		return await GeoPNG.processTimeseriesParallel({
			concurrency: options.concurrency || 8,
			items: target_years,
			name: "Professions E_clampToPercentagesAndAggregates",
			task_generator: (year) => ({
				type: "clamp_professions",
				age_sex_folder: global.age_sex.output_rasters,
				categories: categories,
				gdp_pc_path: (typeof GDP_pc !== "undefined" && GDP_pc.output_gdp_pc_folder) ? path.join(GDP_pc.output_gdp_pc_folder, `GDP_pc_${year}.png`) : `${global.h3 || "./histmap/3.data_transform/"}GDP_pc/8.GDP_nominal_pc_rasters/GDP_pc_${year}.png`,
				geocode_path: (typeof admin_modern !== "undefined") ? admin_modern.input_geocodes_raster : `${global.h1 || "./histmap/1.data_raw/"}admin_modern/geocodes.png`,
				lfpr_folder: LFPR_OLS.output_lfpr_rates,
				logit_rasters_folder: this.intermediate_logit_rasters,
				olivetti_categories: olivetti_categories,
				output_aggregates: output_aggregates,
				output_percentages: output_percentages,
				rur_path: `${global.h2 || "./histmap/2.data_cleaning/"}population_Stadester/stadester_rural_rasters/stadester_rural_${year}.png`,
				sector_baselines: { f: this.getDynamicSectorBaselines(year, "f"), m: this.getDynamicSectorBaselines(year, "m") },
				sexes: sexes,
				target_folder: (typeof professions_Olivetti !== "undefined") ? professions_Olivetti.output_rasters : `${global.h1 || "./histmap/1.data_raw/"}professions_Olivetti/output_rasters/`,
				urb_path: `${global.h2 || "./histmap/2.data_cleaning/"}population_Stadester/stadester_urban_rasters/stadester_urban_${year}.png`,
				working_cohorts: working_cohorts,
				year: year
			}),
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

					let missing_probs = false, prob_rasters = {};

					for (let i = 0; i < olivetti_categories.length; i++) {
						let path = `${this.intermediate_logit_rasters}logit_${sex}_${year}_class_${olivetti_categories[i]}.png`;
						if (!fs.existsSync(path)) { missing_probs = true; break; }
						prob_rasters[olivetti_categories[i]] = GeoPNG.loadNumberRasterImage(path, { format: "float32" });
					}

					if (missing_probs) continue;

					let geocode_data = null, geocode_path = (typeof admin_modern !== "undefined") ? admin_modern.input_geocodes_raster : `${global.h1 || "./histmap/1.data_raw/"}admin_modern/geocodes.png`;
					if (geocode_path && fs.existsSync(geocode_path)) {
						if (!global._cached_geocodes_raster || global._cached_geocodes_path !== geocode_path) {
							global._cached_geocodes_raster = GeoPNG.loadImage(geocode_path);
							global._cached_geocodes_path = geocode_path;
						}
						if (global._cached_geocodes_raster) geocode_data = global._cached_geocodes_raster.data;
					}

					let has_targets = false, target_folder = (typeof professions_Olivetti !== "undefined") ? professions_Olivetti.output_rasters : `${global.h1 || "./histmap/1.data_raw/"}professions_Olivetti/output_rasters/`, target_rasters = {};
					if (target_folder && fs.existsSync(target_folder)) {
						let all_exist = true;
						for (let i = 0; i < olivetti_categories.length; i++) {
							let tp = `${target_folder}${olivetti_categories[i]}_${sex}_${year}.png`;
							if (!fs.existsSync(tp)) { all_exist = false; break; }
						}
						if (all_exist) {
							has_targets = true;
							for (let i = 0; i < olivetti_categories.length; i++) {
								let tp = `${target_folder}${olivetti_categories[i]}_${sex}_${year}.png`;
								target_rasters[olivetti_categories[i]] = GeoPNG.loadNumberRasterImage(tp, { format: "float32" });
							}
						}
					}

					let gdp_pc_path = (typeof GDP_pc !== "undefined" && GDP_pc.output_gdp_pc_folder) ? path.join(GDP_pc.output_gdp_pc_folder, `GDP_pc_${year}.png`) : `${global.h3 || "./histmap/3.data_transform/"}GDP_pc/8.GDP_nominal_pc_rasters/GDP_pc_${year}.png`;
					let urb_path = `${global.h2 || "./histmap/2.data_cleaning/"}population_Stadester/stadester_urban_rasters/stadester_urban_${year}.png`;
					let rur_path = `${global.h2 || "./histmap/2.data_cleaning/"}population_Stadester/stadester_rural_rasters/stadester_rural_${year}.png`;

					let gdp_raster = fs.existsSync(gdp_pc_path) ? GeoPNG.loadNumberRasterImage(gdp_pc_path, { format: "float32" }) : null;
					let rur_raster = fs.existsSync(rur_path) ? GeoPNG.loadNumberRasterImage(rur_path, { format: "float32" }) : null;
					let urb_raster = fs.existsSync(urb_path) ? GeoPNG.loadNumberRasterImage(urb_path, { format: "float32" }) : null;

					let country_stats = {};
					let p0 = prob_rasters[olivetti_categories[0]].data;
					let p1 = prob_rasters[olivetti_categories[1]].data;
					let p2 = prob_rasters[olivetti_categories[2]].data;
					let p3 = prob_rasters[olivetti_categories[3]].data;
					let t0 = (has_targets) ? target_rasters[olivetti_categories[0]].data : null;
					let t1 = (has_targets) ? target_rasters[olivetti_categories[1]].data : null;
					let t2 = (has_targets) ? target_rasters[olivetti_categories[2]].data : null;
					let t3 = (has_targets) ? target_rasters[olivetti_categories[3]].data : null;

					for (let j = 0; j < data_len; j++) {
						let pop = pop_raster[j];
						if (pop <= 0) continue;

						let cid = 0;
						if (geocode_data) {
							let b_idx = j * 4;
							cid = (geocode_data[b_idx] << 16) | (geocode_data[b_idx + 1] << 8) | geocode_data[b_idx + 2];
						}
						if (!country_stats[cid])
							country_stats[cid] = { gdp_sum: 0, model_sum: [0, 0, 0, 0], pop: 0, rur_sum: 0, target_sum: [0, 0, 0, 0], urb_sum: 0 };

						let cs = country_stats[cid];
						cs.pop += pop;
						if (gdp_raster && !isNaN(gdp_raster.data[j])) cs.gdp_sum += gdp_raster.data[j] * pop;
						if (urb_raster && !isNaN(urb_raster.data[j])) cs.urb_sum += urb_raster.data[j];
						if (rur_raster && !isNaN(rur_raster.data[j])) cs.rur_sum += rur_raster.data[j];

						let p_0 = Math.max(1e-5, p0[j] || 0);
						let p_1 = Math.max(1e-5, p1[j] || 0);
						let p_2 = Math.max(1e-5, p2[j] || 0);
						let p_3 = Math.max(1e-5, p3[j] || 0);

						let sum_p = p_0 + p_1 + p_2 + p_3;
						let norm_p = (sum_p > 0) ? (1 / sum_p) : 0.25;
						cs.model_sum[0] += p_0 * norm_p * pop;
						cs.model_sum[1] += p_1 * norm_p * pop;
						cs.model_sum[2] += p_2 * norm_p * pop;
						cs.model_sum[3] += p_3 * norm_p * pop;

						if (has_targets) {
							let tag = t0[j] || 0, tmf = t1[j] || 0, tse = t2[j] || 0, tinf = t3[j] || 0;
							if (tag + tmf + tse + tinf > 0) {
								cs.target_sum[0] += tag * pop;
								cs.target_sum[1] += tmf * pop;
								cs.target_sum[2] += tse * pop;
								cs.target_sum[3] += tinf * pop;
							}
						}
					}

					let country_factors = {};

					for (let cid in country_stats) {
						let cs = country_stats[cid];
						let f = [1, 1, 1, 1];
						let target = null;
						let tot_target = cs.target_sum[0] + cs.target_sum[1] + cs.target_sum[2] + cs.target_sum[3];

						let avg_gdp = (cs.pop > 0) ? (cs.gdp_sum / cs.pop) : 800;
						let tot_urb_rur = cs.urb_sum + cs.rur_sum;
						let urb_rate = (tot_urb_rur > 0) ? (cs.urb_sum / tot_urb_rur) : 0.08;
						let struct_target = this.getCountryStructuralBaselines(avg_gdp, urb_rate, year, sex);

						if (tot_target > 0) {
							let emp_inf = cs.target_sum[3] / tot_target;
							if (emp_inf < 0.005) {
								let inf_share = struct_target.informal_labour;
								let tot_formal = cs.target_sum[0] + cs.target_sum[1] + cs.target_sum[2];
								if (tot_formal > 0) {
									let scale = (1.0 - inf_share) / tot_formal;
									target = {
										agriculture: cs.target_sum[0] * scale,
										manufacturing: cs.target_sum[1] * scale,
										services: cs.target_sum[2] * scale,
										informal_labour: inf_share
									};
								} else {
									target = struct_target;
								}
							} else {
								target = {
									agriculture: cs.target_sum[0] / tot_target,
									manufacturing: cs.target_sum[1] / tot_target,
									services: cs.target_sum[2] / tot_target,
									informal_labour: emp_inf
								};
							}
						} else {
							target = struct_target;
						}

						if (target && cs.pop > 0) {
							let m0 = cs.model_sum[0] / cs.pop;
							let m1 = cs.model_sum[1] / cs.pop;
							let m2 = cs.model_sum[2] / cs.pop;
							let m3 = cs.model_sum[3] / cs.pop;

							f[0] = (m0 > 1e-6) ? (target.agriculture / m0) : ((target.agriculture > 0) ? 1.0 : 0.0);
							f[1] = (m1 > 1e-6) ? (target.manufacturing / m1) : ((target.manufacturing > 0) ? 1.0 : 0.0);
							f[2] = (m2 > 1e-6) ? (target.services / m2) : ((target.services > 0) ? 1.0 : 0.0);
							f[3] = (m3 > 1e-6) ? (target.informal_labour / m3) : ((target.informal_labour > 0) ? 1.0 : 0.0);
						}
						country_factors[cid] = f;
					}

					let agg_arrays = {};
					let pct_arrays = {};
					for (let i = 0; i < categories.length; i++) {
						let c = categories[i];
						agg_arrays[c] = new Float32Array(data_len);
						pct_arrays[c] = new Float32Array(data_len);
						if (!agg_t[c]) agg_t[c] = new Float32Array(data_len);
					}

					let pct_c0 = pct_arrays[olivetti_categories[0]];
					let pct_c1 = pct_arrays[olivetti_categories[1]];
					let pct_c2 = pct_arrays[olivetti_categories[2]];
					let pct_c3 = pct_arrays[olivetti_categories[3]];
					let pct_niw = pct_arrays["not_in_work"];

					let agg_c0 = agg_arrays[olivetti_categories[0]];
					let agg_c1 = agg_arrays[olivetti_categories[1]];
					let agg_c2 = agg_arrays[olivetti_categories[2]];
					let agg_c3 = agg_arrays[olivetti_categories[3]];
					let agg_niw = agg_arrays["not_in_work"];

					let agg_t0 = agg_t[olivetti_categories[0]];
					let agg_t1 = agg_t[olivetti_categories[1]];
					let agg_t2 = agg_t[olivetti_categories[2]];
					let agg_t3 = agg_t[olivetti_categories[3]];
					let agg_t_niw = agg_t["not_in_work"];

					for (let j = 0; j < data_len; j++) {
						let pop = pop_raster[j];
						if (pop <= 0) continue;

						let lfpr = lfpr_raster.data[j];
						if (isNaN(lfpr)) lfpr = 0;

						let cid = 0;
						if (geocode_data) {
							let b_idx = j * 4;
							cid = (geocode_data[b_idx] << 16) | (geocode_data[b_idx + 1] << 8) | geocode_data[b_idx + 2];
						}
						let f = country_factors[cid] || [1, 1, 1, 1];

						let p_0 = Math.max(1e-5, p0[j] || 0);
						let p_1 = Math.max(1e-5, p1[j] || 0);
						let p_2 = Math.max(1e-5, p2[j] || 0);
						let p_3 = Math.max(1e-5, p3[j] || 0);

						let u0 = p_0 * f[0];
						let u1 = p_1 * f[1];
						let u2 = p_2 * f[2];
						let u3 = p_3 * f[3];
						let sum_u = u0 + u1 + u2 + u3;

						let norm_u = (sum_u > 0) ? (lfpr / sum_u) : 0;
						let b_u = (sum_u > 0) ? 0 : (lfpr * 0.25);
						let final_0 = u0 * norm_u + b_u;
						let final_1 = u1 * norm_u + b_u;
						let final_2 = u2 * norm_u + b_u;
						let final_3 = u3 * norm_u + b_u;
						let final_niw = Math.max(0, 1.0 - lfpr);

						pct_c0[j] = final_0;
						pct_c1[j] = final_1;
						pct_c2[j] = final_2;
						pct_c3[j] = final_3;
						pct_niw[j] = final_niw;

						let a0 = final_0 * pop;
						let a1 = final_1 * pop;
						let a2 = final_2 * pop;
						let a3 = final_3 * pop;
						let aniw = final_niw * pop;

						agg_c0[j] = a0;
						agg_c1[j] = a1;
						agg_c2[j] = a2;
						agg_c3[j] = a3;
						agg_niw[j] = aniw;

						agg_t0[j] += a0;
						agg_t1[j] += a1;
						agg_t2[j] += a2;
						agg_t3[j] += a3;
					}

					for (let i = 0; i < categories.length; i++) {
						let c = categories[i];
						GeoPNG.saveNumberRasterImage({ file_path: `${output_percentages}${c}_${sex}_${year}.png`, format: "float32", height: height, width: width, function: (idx) => pct_arrays[c][idx] });
						GeoPNG.saveNumberRasterImage({ file_path: `${output_aggregates}${c}_${sex}_${year}.png`, format: "float32", height: height, width: width, function: (idx) => agg_arrays[c][idx] });
					}
				}
				
				if (pop_t) {
					for (let i = 0; i < categories.length; i++) {
						let c = categories[i];
						GeoPNG.saveNumberRasterImage({ file_path: `${output_percentages}${c}_t_${year}.png`, format: "float32", height: height, width: width, function: (idx) => (pop_t[idx] > 0) ? (agg_t[c][idx] / pop_t[idx]) : 0 });
						GeoPNG.saveNumberRasterImage({ file_path: `${output_aggregates}${c}_t_${year}.png`, format: "float32", height: height, width: width, function: (idx) => agg_t[c][idx] });
					}
				}
			}
		});
	}

	/**
	 * Computes structural sectoral employment baselines anchored to country GDP per capita and urbanisation.
	 * Clark-Fisher/Kuznets structural baselines, with empirical non-linear regressions based on Hollis Chenery & Moises Syrquin (1975).
	 *
	 * @alias professions.getCountryStructuralBaselines
	 * @param {number} [arg0_gdp_pc=1000] - Real GDP per capita in 2017 USD PPP.
	 * @param {number} [arg1_urb_rate=0.10] - National urbanisation proportion (0 to 1).
	 * @param {number} [arg2_year=1860] - Target calendar year.
	 * @param {string} [arg3_sex="m"] - Target sex ("m" or "f").
	 *
	 * @returns {{agriculture: number, manufacturing: number, services: number, informal_labour: number}}
	 */
	static getCountryStructuralBaselines (arg0_gdp_pc, arg1_urb_rate, arg2_year, arg3_sex) {
		//Convert from parameters
		let gdp_pc = Math.returnSafeNumber(arg0_gdp_pc, 1000);
		let urb_rate = Math.returnSafeNumber(arg1_urb_rate, 0.10);
		let year = Math.returnSafeNumber(arg2_year, 1860);
		let sex = (arg3_sex || "m").toLowerCase();

		//Declare local instance variables
		let agri = 0.50;
		let inf = (sex === "f") ? 0.05 : 0.04;
		let mfg = 0.25;
		let serv = 0.20;

		//1. Historical Era (prior to or at 1890): Industrial transition structural scaling (Chenery & Syrquin, 1975)
		if (year <= 1890) {
			let u = Math.min(0.85, Math.max(0.01, urb_rate));
			let z = Math.max(0, Math.log(Math.max(350, gdp_pc) / 350));

			inf = (sex === "f") ? (0.045 + 0.03 / (1 + z)) : (0.035 + 0.025 / (1 + z));
			mfg = (sex === "f" ? 0.05 : 0.04) + 0.022 * z + 0.42 * u * Math.sqrt(z) + 0.48 * Math.pow(u, 1.8) * z;
			mfg = Math.min(0.55, Math.max(0.04, mfg));

			agri = (sex === "f" ? 0.82 : 0.85) - 0.12 * z - 0.65 * Math.pow(u, 0.75) * (1 + 0.15 * z);
			agri = Math.min(0.88, Math.max(0.08, agri));

			serv = Math.max(0.06, 1.0 - agri - mfg - inf);
			let sum = agri + mfg + serv + inf;
			agri /= sum;
			mfg /= sum;
			serv /= sum;
			inf /= sum;
		} else {
			//2. Modern Era (post-1890): Post-industrial tertiary shift (Chenery & Syrquin, 1975 / Kuznets)
			let u = Math.min(0.95, Math.max(0.02, urb_rate));
			let z = Math.max(300, gdp_pc);

			inf = (sex === "f") ? (0.035 + 0.18 / (1 + Math.pow(z / 2200, 1.3))) : (0.025 + 0.15 / (1 + Math.pow(z / 2200, 1.3)));
			agri = 0.02 + 0.78 / (1 + Math.pow(z / 1400, 1.1) + 2.5 * Math.pow(u, 1.5));
			let mfg_curve = 0.12 + 0.18 * Math.exp(-0.5 * Math.pow((Math.log(z / 1000) - 2.2) / 1.1, 2));
			mfg = mfg_curve * (0.6 + 0.6 * Math.pow(u, 0.8));
			mfg = Math.min(0.50, Math.max(0.05, mfg));
			agri = Math.min(0.85, Math.max(0.01, agri));

			serv = Math.max(0.10, 1.0 - agri - mfg - inf);
			let sum = agri + mfg + serv + inf;
			agri /= sum;
			mfg /= sum;
			serv /= sum;
			inf /= sum;
		}

		//Return statement
		return { agriculture: agri, manufacturing: mfg, services: serv, informal_labour: inf };
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
				{ y: 1890, m: { agriculture: 0.650, manufacturing: 0.175, services: 0.135, informal_labour: 0.040 }, f: { agriculture: 0.620, manufacturing: 0.150, services: 0.170, informal_labour: 0.060 } },
				{ y: 1950, m: { agriculture: 0.550, manufacturing: 0.230, services: 0.180, informal_labour: 0.040 }, f: { agriculture: 0.540, manufacturing: 0.180, services: 0.230, informal_labour: 0.050 } },
				{ y: 2000, m: { agriculture: 0.400, manufacturing: 0.230, services: 0.330, informal_labour: 0.040 }, f: { agriculture: 0.380, manufacturing: 0.170, services: 0.410, informal_labour: 0.040 } },
				{ y: 2025, m: { agriculture: 0.270, manufacturing: 0.230, services: 0.460, informal_labour: 0.040 }, f: { agriculture: 0.230, manufacturing: 0.160, services: 0.570, informal_labour: 0.040 } }
			];
			let lower = milestones[0], upper = milestones[milestones.length - 1];
			for (let i = 0; i < milestones.length - 1; i++)
				if (year >= milestones[i].y && year <= milestones[i + 1].y) { lower = milestones[i]; upper = milestones[i + 1]; break; }

			let t = (upper.y === lower.y) ? 0 : (year - lower.y) / (upper.y - lower.y), s = t*t*(3 - 2*t);
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
			let base_1890 = (sex === "f") ? { agriculture: 0.620, manufacturing: 0.150, services: 0.170, informal_labour: 0.060 } : { agriculture: 0.650, manufacturing: 0.175, services: 0.135, informal_labour: 0.040 };
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
			return { agriculture: Math.max(0.60, 1.0 - serv - mfg - inf), manufacturing: mfg, services: serv, informal_labour: inf };
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