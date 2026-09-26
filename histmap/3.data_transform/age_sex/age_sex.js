global.age_sex = class {
	static cf = `${h3}/age_sex/`;
	static hf = () => `${landuse_HYDE.bf}/rasters/`;
	static hf1 = (y) => landuse_HYDE._getHYDEYearName(y);
	static sf = () => population_Stadester;
	
	static covariates_obj = {
		//LU (Land Use)
		"conv_rangeland": (y) => [`${this.hf()}/conv_rangeland${this.hf1(y)}_number.png`, "float32"],
		"cropland": (y) => [`${this.hf()}/cropland${this.hf1(y)}_number.png`, "float32"],
		"grazing": (y) => [`${this.hf()}/grazing${this.hf1(y)}_number.png`, "float32"],
		"ir_norice": (y) => [`${this.hf()}/ir_norice${this.hf1(y)}_number.png`, "float32"],
		"ir_rice": (y) => [`${this.hf()}/ir_rice${this.hf1(y)}_number.png`, "float32"],
		"pasture": (y) => [`${this.hf()}/pasture${this.hf1(y)}_number.png`, "float32"],
		"rangeland": (y) => [`${this.hf()}/rangeland${this.hf1(y)}_number.png`, "float32"],
		"rf_norice": (y) => [`${this.hf()}/rf_norice${this.hf1(y)}_number.png`, "float32"],
		"rf_rice": (y) => [`${this.hf()}/rf_rice${this.hf1(y)}_number.png`, "float32"],
		"shifting": (y) => [`${this.hf()}/shifting${this.hf1(y)}_number.png`, "float32"],
		"tot_irri": (y) => [`${this.hf()}/tot_irri${this.hf1(y)}_number.png`, "float32"],
		"tot_rainfed": (y) => [`${this.hf()}/tot_rainfed${this.hf1(y)}_number.png`, "float32"],
		"tot_rice": (y) => [`${this.hf()}/tot_rice${this.hf1(y)}_number.png`, "float32"],
		"uopp_": (y) => [`${this.hf()}/uopp_${this.hf1(y)}_number.png`, "float32"],
		
		//POP (Demographics)
		"popc_": (y) => [`${this.sf().input_popc_folder}/stadester_population_${y}.png`, "float32"],
		"popd_": (y) => [`${this.sf().intermediate_popd_folder}/stadester_density_${y}.png`, "float32"],
		"rurc_": (y) => [`${this.sf().input_rurc_folder}/stadester_rural_${y}.png`, "float32"],
		"urbc_": (y) => [`${this.sf().input_urbc_folder}/stadester_urban_${y}.png`, "float32"],
		
		//Eoscala (Economics)
		"discretionary_income": (y) => [`${wealth_income.output_discretionary_income_folder}/discretionary_income_${y}.png`, "float32"],
		"disposable_income": (y) => [`${wealth_income.output_disposable_income_folder}/disposable_income_${y}.png`, "float32"],
		"gdp_nominal": (y) => [`${GDP_pc.intermediate_gdp_scaled_to_national}/GDP_${y}.png`, "float32"],
		"gdp_pc": (y) => [`${GDP_pc.output_gdp_pc_folder}/GDP_pc_${y}.png`, "float32"],
		"gdp_ppp": (y) => [`${GDP_PPP_pc.intermediate_gdp_ppp_scaled_to_national}/GDP_PPP_${y}.png`, "float32"],
		"gdp_ppp_pc": (y) => [`${GDP_PPP_pc.output_gdp_ppp_pc_folder}/GDP_PPP_pc_${y}.png`, "float32"],
		"gini": (y) => [`${gini_Eoscala.output_rasters}gini_${y}.png`, "float32"],
		"net_income": (y) => [`${wealth_income.output_net_income_folder}/net_income_${y}.png`, "float32"],
		"net_wealth": (y) => [`${wealth_income.output_net_wealth_folder}/net_wealth_${y}.png`, "float32"],
		
		//Deltas (Economics, Demographics)
		"delta_gdp_nominal": (y) => [`${GDP_Eoscala_transform.delta_GDP_nominal_folder}/delta_GDP_${y}.png`, "float32"],
		"delta_gdp_pc": (y) => [`${GDP_Eoscala_transform.delta_GDP_pc_folder}/delta_GDP_pc_${y}.png`, "float32"],
		"delta_gdp_ppp": (y) => [`${GDP_Eoscala_transform.delta_GDP_PPP_folder}/delta_GDP_PPP_${y}.png`, "float32"],
		"delta_gdp_ppp_pc": (y) => [`${GDP_Eoscala_transform.delta_GDP_PPP_pc_folder}/delta_GDP_PPP_pc_${y}.png`, "float32"],
		"delta_popd_": (y) => [`${population_Stadester_transform.delta_population_density_folder}/delta_population_density_${y}.png`, "float32"],
		
		"delta_popc_": (y) => [`${population_Stadester_transform.delta_total_population_folder}/delta_total_population_${y}.png`, "float32"],
		"delta_rurc_": (y) => [`${population_Stadester_transform.delta_rural_population_folder}/delta_rural_population_${y}.png`, "float32"],
		"delta_urbc_": (y) => [`${population_Stadester_transform.delta_urban_population_folder}/delta_urban_population_${y}.png`, "float32"]
	};
	
	static standardised_targets_folder = `${this.cf}/0.standardised_targets/`;
	static intermediate_logit_folder = `${this.cf}/1.multinomial_logit/`;
	static intermediate_logit_rasters = `${this.cf}/2.logit_rasters/`;
	static intermediate_clamped_rasters = `${this.cf}/3.clamped_to_stadester/`;
	static output_rasters = `${this.cf}/4.composite_cohorts/`;
	
	/**
	 * Helper function to generate standard WorldPop bucket names.
	 * @returns {Array<string>}
	 */
	static getCohorts () {
		let age_groups = ["00", "01"];
		for (let i = 5; i <= 80; i += 5) age_groups.push(i.toString().padStart(2, "0"));
		
		let cohorts = [];
		for (let i = 0; i < age_groups.length; i++) {
			cohorts.push(`f_${age_groups[i]}`);
			cohorts.push(`m_${age_groups[i]}`);
		}
		return cohorts;
	}
	
	/**
	 * Standardises HMD, UNWPP, and WorldPop datasets into a unified target pool (1750-2025).
	 */
	static async A_standardiseTargets (arg0_options) {
		let options = (arg0_options) ? arg0_options : {};
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;

		if (!fs.existsSync(this.standardised_targets_folder)) fs.mkdirSync(this.standardised_targets_folder, { recursive: true });
		
		let cohorts = this.getCohorts();
		let copy_tasks = [];
		let train_years = (options.years) ? options.years : landuse_HYDE.sorted_hyde_years.filter(y => y >= 1750 && y <= 2025);
		let wp_files = [];
		
		if (typeof age_sex_WorldPop !== "undefined" && fs.existsSync(age_sex_WorldPop.output_rasters)) {
			wp_files = fs.readdirSync(age_sex_WorldPop.output_rasters);
		}
		
		for (let y = 0; y < train_years.length; y++) {
			let year = train_years[y];
			
			for (let c = 0; c < cohorts.length; c++) {
				let cohort = cohorts[c];
				let out_path = `${this.standardised_targets_folder}global_${cohort}_${year}.png`;
				
				if (!overwrite && fs.existsSync(out_path)) continue;
				
				let src_path = null;
				if (year < 1950) {
					src_path = `${age_sex_HMD.output_clamped_to_stadester}global_${cohort}_${year}.png`;
				} else if (year >= 1950 && year < 2015) {
					src_path = `${age_sex_UNWPP.output_clamped_to_stadester}global_${cohort}_${year}.png`;
				} else if (year >= 2015) {
					let regex = new RegExp(`^.*${cohort}_${year}.*\\.png$`);
					let wp_match = wp_files.find(f => regex.test(f));
					if (wp_match) {
						src_path = `${age_sex_WorldPop.output_rasters}${wp_match}`;
					} else {
						let unwpp_fallback = `${age_sex_UNWPP.output_clamped_to_stadester}global_${cohort}_${year}.png`;
						if (fs.existsSync(unwpp_fallback)) src_path = unwpp_fallback;
					}
				}
				
				if (src_path && fs.existsSync(src_path)) {
					copy_tasks.push({
						dest: out_path,
						src: src_path
					});
				}
			}
		}
		
		if (copy_tasks.length > 0) {
			await GeoPNG.processTimeseriesParallel({
				concurrency: options.concurrency || 8,
				items: copy_tasks,
				name: "age_sex A_standardiseTargets",
				task_generator: (task_item) => ({
					dest_path: task_item.dest,
					source_path: task_item.src,
					task_type: "copy"
				})
			});
		}
		console.log(`Standardised target pool mapped across the timeseries.`);
	}
	
	/**
	 * Trains temporally discrete multinomial models year-by-year utilizing 100% of the active raster.
	 */
	static async B_trainMultinomialLogitModels (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
		
		//Declare local instance variables
		let cohorts = this.getCohorts();
		let target_years = (options.years) ? options.years : landuse_HYDE.sorted_hyde_years.filter(y => y >= 1750 && y <= 2025);
		
		if (!fs.existsSync(this.intermediate_logit_folder)) fs.mkdirSync(this.intermediate_logit_folder, { recursive: true });
		
		target_years = target_years.filter((year) => {
			let model_path = `${this.intermediate_logit_folder}multinomial_model_${year}.json`;
			let target_path = `${this.standardised_targets_folder}global_${cohorts[0]}_${year}.png`;
			if (!fs.existsSync(target_path)) return false;
			return (overwrite || !fs.existsSync(model_path));
		});
		
		if (target_years.length === 0) return [];
		
		//Return statement
		return Statistics.trainMultinomialLogitModelsParallel(target_years, (year) => {
			let all_keys = Object.keys(this.covariates_obj);
			let covariates_map = {};
			let format_year = year > 2023 ? 2023 : year;
			let model_path = `${this.intermediate_logit_folder}multinomial_model_${year}.json`;
			let popc_info = this.covariates_obj["popc_"](format_year);
			let target_paths = {};
			
			for (let i = 0; i < all_keys.length; i++) {
				let k = all_keys[i];
				let info = this.covariates_obj[k](format_year);
				covariates_map[k] = info;
			}
			
			for (let i = 0; i < cohorts.length; i++) {
				let c = cohorts[i];
				target_paths[c] = `${this.standardised_targets_folder}global_${c}_${year}.png`;
			}
			
			return {
				categories: cohorts,
				covariates_map: covariates_map,
				filter_format: (popc_info && popc_info[1]) ? popc_info[1] : "float32",
				filter_raster_path: (popc_info) ? popc_info[0] : null,
				model_path: model_path,
				options: {
					debug: true,
					fit_intercept: (options.fit_intercept !== undefined) ? options.fit_intercept : false,
					lambda: Math.returnSafeNumber(options.lambda, 0),
					learning_rate: Math.returnSafeNumber(options.learning_rate, 0.1),
					max_iterations: Math.returnSafeNumber(options.max_iterations, 50),
					sample_limit: Math.returnSafeNumber(options.sample_limit, 15000),
					tolerance: Math.returnSafeNumber(options.tolerance, 1e-4)
				},
				target_paths: target_paths
			};
		}, {
			concurrency: options.concurrency,
			name: "Age Sex Multinomial Logit Training"
		});
	}
	
	/**
	 * Merges all trained yearly multinomial logit models into a single coverage-weighted 'Unified' ensemble
	 * to prevent single-country distortion (e.g. 1750 Sweden) and eliminates arithmetic coefficient averaging.
	 */
	static async C_mergeMultinomialLogitModels (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;

		//Declare local instance variables
		let cohorts = this.getCohorts();
		let ensemble_models = [];
		let max_samples = 1;
		let models_loaded = 0;
		let raw_models = [];
		let train_years = (options.years) ? options.years : landuse_HYDE.sorted_hyde_years.filter(y => y >= 1750 && y <= 2025);
		let unified_path = `${this.intermediate_logit_folder}multinomial_model_unified.json`;
		let weights_path = `${this.intermediate_logit_folder}anchor_coverage_weights.json`;

		if (!overwrite && fs.existsSync(unified_path)) {
			console.log(`Unified Multinomial Logit model already exists. Skipping merge.`);
			return;
		}
		
		console.log(`Generating coverage-weighted unified historical MNL ensemble...`);
		
		//1. Load temporal models and compute empirical sample coverage
		for (let y = 0; y < train_years.length; y++) {
			let year = train_years[y];
			let p = `${this.intermediate_logit_folder}multinomial_model_${year}.json`;
			
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
		
		if (models_loaded === 0) {
			console.warn(`[WARN] No temporal models found to merge!`);
			return;
		}
		
		//2. Calculate coverage-weighted utility weights: C_t = (samples/max_samples)^0.3
		let total_coverage_weight = 0;
		for (let i = 0; i < raw_models.length; i++) {
			let entry = raw_models[i];
			let coverage_metric = Math.pow(entry.sample_count/max_samples, 0.3); //[WIP] - Magic number: why 0.3?
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
		
		//3. Assemble unified ensemble artifact
		let unified_model = {
			classes: cohorts,
			models: ensemble_models,
			sample_count_max: max_samples,
			total_anchors: models_loaded,
			type: "multinomial_ensemble"
		};
		
		fs.writeFileSync(unified_path, JSON.stringify(unified_model, null, 2));
		fs.writeFileSync(weights_path, JSON.stringify(ensemble_models, null, 2));
		console.log(`Unified coverage-weighted MNL ensemble generated and saved using ${models_loaded} historical temporal anchors.`);
	}
	
	/**
	 * Generates cohort probabilities. Uses specific temporal models where available,
	 * premodern NDT model for pre-1500 Columbian exchange era, and coverage-weighted ensemble blending for gaps.
	 */
	static async D_generateMultinomialLogitRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
		
		//Declare local instance variables
		let check_cohort = this.getCohorts()[0];
		let years = (options.years) ? options.years : landuse_HYDE.sorted_hyde_years;
		
		if (!fs.existsSync(this.intermediate_logit_rasters)) fs.mkdirSync(this.intermediate_logit_rasters, { recursive: true });
		
		let target_years = years.filter((year) => {
			let out_base = `${this.intermediate_logit_rasters}logit_${year}.png`;
			let check_path = out_base.replace(".png", `_class_${check_cohort}.png`);
			return (overwrite || !fs.existsSync(check_path));
		});
		
		if (target_years.length === 0) return [];
		
		//Return statement
		return Statistics.generateMultinomialRastersParallel(target_years, (year) => {
			let all_keys = Object.keys(this.covariates_obj);
			let covariates_map = {};
			let format_year = year > 2023 ? 2023 : year;
			let model_path = `${this.intermediate_logit_folder}multinomial_model_${year}.json`;
			let out_base = `${this.intermediate_logit_rasters}logit_${year}.png`;
			let has_local_anchor = fs.existsSync(model_path);
			let resolved_model = model_path;
			let unified_path = `${this.intermediate_logit_folder}multinomial_model_unified.json`;
			
			//Regime 1: Pre-1500 AD (Columbian Exchange Breakpoint) > NDT Premodern land-use model
			if (year < 1500) {
				let premodern_path = `${this.intermediate_logit_folder}premodern_multinomial_logit.json`;
				if (fs.existsSync(premodern_path)) resolved_model = premodern_path;
			} else if (fs.existsSync(unified_path)) {
				//Regime 2: Post-1500 AD > Coverage-weighted temporal kernel ensemble (blended 80/20 with local anchor if available)
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
						classes: this.getCohorts(),
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
			
			if (!resolved_model) return null;
			
			for (let i = 0; i < all_keys.length; i++) {
				let k = all_keys[i];
				let info = this.covariates_obj[k](format_year);
				covariates_map[k] = info;
			}
			
			return {
				covariates_map: covariates_map,
				model_obj: resolved_model,
				options: {
					format: "float32",
					mask_uninhabited: true,
					output_mode: "probabilities"
				},
				output_file_path: out_base
			};
		}, {
			concurrency: options.concurrency,
			name: "Age Sex Multinomial Logit Raster Generation"
		});
	}
	
	static async E_clampToStadester (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};

		//Initialise options
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
		let years = (options.years) ? options.years : landuse_HYDE.sorted_hyde_years;
		let smoothing_method = options.smoothing_method || "whittaker_henderson";
		let do_not_smooth = !!(options.do_not_smooth || options.lift_isotonic);
		let use_whittaker = (smoothing_method === "whittaker_henderson");
		let use_global_scaling = !do_not_smooth && options.global_cohort_scaling !== false;
		let start_index = (options.smoothing_start_index !== undefined) ? options.smoothing_start_index : 2;

		//Whittaker sex-ratio policies are opt-in, matching the new coupling method
		let enforce_fixed = (options.enforce_fixed_sex_ratios === true);
		let enforce_bounds = (options.enforce_biological_sex_ratios === true);
		let preserve_sex_ratios = (options.preserve_sex_ratios !== undefined) ?
			options.preserve_sex_ratios : !enforce_fixed && !enforce_bounds;

		//Declare local instance variables
		let cohorts = this.getCohorts();
		let num_cohorts = cohorts.length;
		let f_indices = [];
		let m_indices = [];
		let completed_years = [];

		//Guard clauses
		if (smoothing_method !== "whittaker_henderson" && smoothing_method !== "isotonic")
			throw new RangeError("smoothing_method must be 'whittaker_henderson' or 'isotonic'.");

		if (!Number.isInteger(start_index) || start_index < 0)
			throw new RangeError("smoothing_start_index must be a non-negative integer.");

		if (use_whittaker && typeof Statistics.coupleAgeSexCohortsWhittaker !== "function")
			throw new Error("Statistics.coupleAgeSexCohortsWhittaker is not available.");

		if (!use_whittaker && typeof Statistics.coupleAgeSexCohorts !== "function")
			throw new Error("Statistics.coupleAgeSexCohorts is not available.");

		if (use_whittaker && preserve_sex_ratios && (enforce_fixed || enforce_bounds))
			throw new Error("Preserving raw sex ratios conflicts with fixed ratios or ratio bounds.");

		if (!fs.existsSync(this.intermediate_clamped_rasters))
			fs.mkdirSync(this.intermediate_clamped_rasters, { recursive: true });

		//Match female and male cohorts explicitly by age label
		for (let c = 0; c < num_cohorts; c++) {
			if (!cohorts[c].startsWith("f_"))
				continue;

			let age_label = cohorts[c].slice(2);
			let male_index = cohorts.indexOf(`m_${age_label}`);

			if (male_index === -1)
				throw new Error(`Missing male counterpart for ${cohorts[c]}.`);

			f_indices.push(c);
			m_indices.push(male_index);
		}

		let age_count = f_indices.length;

		if (age_count === 0 || age_count*2 !== num_cohorts)
			throw new Error("Cohorts must contain one female and one male entry per age band.");

		let age_band_widths = new Float64Array(age_count);

		if (options.age_band_widths && options.age_band_widths.length !== age_count)
			throw new RangeError("age_band_widths must contain one width per age band.");

		for (let k = 0; k < age_count; k++) {
			let age_label = cohorts[f_indices[k]].slice(2);
			let default_width = (age_label === "00") ? 1 : ((age_label === "01") ? 4 : 5);
			let width = options.age_band_widths ? options.age_band_widths[k] : default_width;

			if (!Number.isFinite(width) || width <= 0)
				throw new RangeError("Age-band widths must be finite and greater than zero.");

			age_band_widths[k] = width;
		}

		let target_years = years.filter((year) => {
			if (overwrite)
				return true;

			for (let c = 0; c < num_cohorts; c++) {
				let out_path = `${this.intermediate_clamped_rasters}global_${cohorts[c]}_${year}.png`;

				if (!fs.existsSync(out_path))
					return true;
			}

			return false;
		});

		if (target_years.length === 0)
			return [];

		return GeoPNG.processTimeseriesParallel({
			concurrency: options.concurrency,
			items: target_years,
			name: `Age Sex Clamping (${smoothing_method})`,
			task_generator: (year) => {
				let format_year = (year > 2023) ? 2023 : year;
				let popc_path = path.join(population_Stadester.input_popc_folder, `stadester_population_${format_year}.png`);
				
				return {
					baseline_sex_ratios: options.baseline_sex_ratios,
					cohorts: cohorts,
					do_not_smooth: do_not_smooth,
					enforce_biological_sex_ratios: enforce_bounds,
					enforce_fixed_sex_ratios: enforce_fixed,
					geocodes_csv_path: (typeof admin_modern !== "undefined") ? admin_modern.input_geocodes_csv : (global.h1 ? path.join(global.h1, "admin_modern/geocodes.csv") : null),
					geocodes_raster_path: (typeof admin_modern !== "undefined") ? admin_modern.input_geocodes_raster : (global.h1 ? path.join(global.h1, "admin_modern/geocodes.png") : null),
					hmd_folder: options.hmd_folder,
					lift_isotonic: do_not_smooth,
					logit_rasters_folder: this.intermediate_logit_rasters,
					output_folder: this.intermediate_clamped_rasters,
					popc_format: "float32",
					popc_path: popc_path,
					preserve_sex_ratios: preserve_sex_ratios,
					smoothing_method: smoothing_method,
					smoothing_start_index: start_index,
					task_type: (use_whittaker) ? "clamp_cohorts_whittaker" : "clamp_cohorts_isotonic",
					wh_huber_delta: options.wh_huber_delta,
					wh_lambda: options.wh_lambda,
					wh_max_iterations: options.wh_max_iterations,
					wh_mu: options.wh_mu,
					wh_tolerance: options.wh_tolerance,
					wh_weights: options.wh_weights,
					year: year
				};
			}
		});
	}
	
	static async F_compositeTimeseries (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;

		//Declare local instance variables
		let cohorts = this.getCohorts();
		let copy_tasks = [];
		let wp_files = [];
		let years = (options.years) ? options.years : landuse_HYDE.sorted_hyde_years;

		if (!fs.existsSync(this.output_rasters)) fs.mkdirSync(this.output_rasters, { recursive: true });
		
		//Cache the WorldPop directory listing once to avoid repeated disk reads
		if (typeof age_sex_WorldPop !== "undefined" && fs.existsSync(age_sex_WorldPop.output_rasters)) {
			wp_files = fs.readdirSync(age_sex_WorldPop.output_rasters);
		}
		
		//Build copy task list across the full temporal domain
		for (let y = 0; y < years.length; y++) {
			let year = years[y];
			
			for (let c = 0; c < cohorts.length; c++) {
				let cohort = cohorts[c];
				let out_path = `${this.output_rasters}${cohort}_${year}.png`;
				
				if (!overwrite && fs.existsSync(out_path)) continue;
				
				let src_path = null;
				
				//1. UNWPP actuals take precedence for 1950-2014
				if (year >= 1950 && year < 2015) {
					if (typeof age_sex_UNWPP !== "undefined" && fs.existsSync(age_sex_UNWPP.output_clamped_to_stadester)) {
						let unwpp_path = `${age_sex_UNWPP.output_clamped_to_stadester}global_${cohort}_${year}.png`;
						if (fs.existsSync(unwpp_path)) src_path = unwpp_path;
					}
				}
				
				//2. WorldPop actuals take precedence for 2015-2025
				if (year >= 2015 && year <= 2025) {
					let regex = new RegExp(`^.*${cohort}_${year}.*\\.png$`);
					let wp_match = wp_files.find(f => regex.test(f));
					
					if (wp_match) {
						src_path = `${age_sex_WorldPop.output_rasters}${wp_match}`;
					} else {
						//Fallback to UNWPP if the specific WorldPop year is missing
						if (typeof age_sex_UNWPP !== "undefined" && fs.existsSync(age_sex_UNWPP.output_clamped_to_stadester)) {
							let unwpp_fallback = `${age_sex_UNWPP.output_clamped_to_stadester}global_${cohort}_${year}.png`;
						if (fs.existsSync(unwpp_fallback)) src_path = unwpp_fallback;
						}
					}
				}
				
				//3. Default to the clamped multinomial logit rasters for all other years (pre-1950, post-2025, or missing actuals)
				if (!src_path) {
					let clamped_path = `${this.intermediate_clamped_rasters}global_${cohort}_${year}.png`;
					if (fs.existsSync(clamped_path)) src_path = clamped_path;
				}
				
				if (src_path) {
					copy_tasks.push({
						dest: out_path,
						src: src_path
					});
				}
			}
		}
		
		if (copy_tasks.length > 0) {
			await GeoPNG.processTimeseriesParallel({
				items: copy_tasks,
				concurrency: options.concurrency || 8,
				name: "age_sex F_compositeTimeseries",
				task_generator: (task_item) => ({
					task_type: "copy",
					dest_path: task_item.dest,
					source_path: task_item.src
				})
			});
		}
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
			console.log(`[age_sex] Skipping Steps A, B & C training (using existing models).`);
		}
		
		if (!options.exclude.includes("A")) await this.A_standardiseTargets(options);
		if (!options.exclude.includes("B")) await this.B_trainMultinomialLogitModels(options);
		if (!options.exclude.includes("C")) await this.C_mergeMultinomialLogitModels(options);
		if (!options.exclude.includes("D")) await this.D_generateMultinomialLogitRasters(options);
		if (!options.exclude.includes("E")) await this.E_clampToStadester(options);
		if (!options.exclude.includes("F")) await this.F_compositeTimeseries(options);
	}
};
