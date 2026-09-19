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
		"gdp_nominal": (y) => [`${GDP_pc.intermediate_gdp_scaled_to_national}/GDP_${y}.png`, "float32"],
		"gdp_pc": (y) => [`${GDP_pc.output_gdp_pc_folder}/GDP_pc_${y}.png`, "float32"],
		"gdp_ppp": (y) => [`${GDP_PPP_pc.intermediate_gdp_ppp_scaled_to_national}/GDP_PPP_${y}.png`, "float32"],
		"gdp_ppp_pc": (y) => [`${GDP_PPP_pc.output_gdp_ppp_pc_folder}/GDP_PPP_pc_${y}.png`, "float32"],
		"discretionary_income": (y) => [`${wealth_income.output_discretionary_income_folder}/discretionary_income_${y}.png`, "float32"],
		"disposable_income": (y) => [`${wealth_income.output_disposable_income_folder}/disposable_income_${y}.png`, "float32"],
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
		let train_years = landuse_HYDE.sorted_hyde_years.filter(y => y >= 1750 && y <= 2025);
		
		for (let y = 0; y < train_years.length; y++) {
			let year = train_years[y];
			let wp_files = [];
			
			if (year >= 2015 && fs.existsSync(age_sex_WorldPop.output_rasters)) {
				wp_files = fs.readdirSync(age_sex_WorldPop.output_rasters);
			}
			
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
					fs.copyFileSync(src_path, out_path);
				}
			}
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
		let target_years = landuse_HYDE.sorted_hyde_years.filter(y => y >= 1750 && y <= 2025);
		
		if (!fs.existsSync(this.intermediate_logit_folder)) fs.mkdirSync(this.intermediate_logit_folder, { recursive: true });
		
		target_years = target_years.filter((year) => {
			let model_path = `${this.intermediate_logit_folder}multinomial_model_${year}.json`;
			return (overwrite || !fs.existsSync(model_path));
		});
		
		if (target_years.length === 0) return [];
		
		//Return statement
		return await Statistics.trainMultinomialLogitModelsParallel(target_years, (year) => {
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
					lambda: Math.returnSafeNumber(options.lambda, 1e-4),
					learning_rate: Math.returnSafeNumber(options.learning_rate, 0.1),
					max_iterations: Math.returnSafeNumber(options.max_iterations, 50)
				},
				target_paths: target_paths
			};
		}, {
			concurrency: options.concurrency,
			name: "Age Sex Multinomial Logit Training"
		});
	}
	
	/**
	 * Merges all trained yearly multinomial logit models into a single 'Unified' model
	 * via arithmetic mean to remove era-specific and spatial biases (e.g. 1750 Sweden).
	 */
	static async C_mergeMultinomialLogitModels (arg0_options) {
		let options = (arg0_options) ? arg0_options : {};
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;

		let unified_path = `${this.intermediate_logit_folder}multinomial_model_unified.json`;
		if (!overwrite && fs.existsSync(unified_path)) {
			console.log(`Unified Multinomial Logit model already exists. Skipping merge.`);
			return;
		}
		
		console.log(`Generating unified historical MNL model from trained ensemble...`);
		
		let train_years = landuse_HYDE.sorted_hyde_years.filter(y => y >= 1750 && y <= 2025);
		let models_loaded = 0;
		let unified_sums = {};
		let ref_class = "";
		let valid_covariates = [];
		
		// Extract and sum coefficients across all available temporal models
		for (let y = 0; y < train_years.length; y++) {
			let year = train_years[y];
			let p = `${this.intermediate_logit_folder}multinomial_model_${year}.json`;
			
			if (fs.existsSync(p)) {
				let m = JSON.parse(fs.readFileSync(p, "utf8"));
				models_loaded++;
				ref_class = m.reference_class;
				valid_covariates = m.covariates;
				
				Object.iterate(m.coefficients, (c_key, covs) => {
					if (!unified_sums[c_key]) unified_sums[c_key] = {};
					
					Object.iterate(covs, (cov_key, val) => {
						if (unified_sums[c_key][cov_key] === undefined) unified_sums[c_key][cov_key] = 0;
						unified_sums[c_key][cov_key] += val;
					});
				});
			}
		}
		
		if (models_loaded === 0) {
			console.warn(`[WARN] No temporal models found to merge!`);
			return;
		}
		
		// Arithmetic Average
		let unified_model = {
			type: "multinomial_logit",
			classes: this.getCohorts(),
			reference_class: ref_class,
			covariates: valid_covariates,
			coefficients: {}
		};
		
		Object.iterate(unified_sums, (c_key, covs) => {
			unified_model.coefficients[c_key] = {};
			Object.iterate(covs, (cov_key, val) => {
				unified_model.coefficients[c_key][cov_key] = val / models_loaded;
			});
		});
		
		fs.writeFileSync(unified_path, JSON.stringify(unified_model, null, 2));
		console.log(`Unified multinomial logit model generated and saved using ${models_loaded} historical temporal anchors.`);
	}
	
	/**
	 * Generates cohort probabilities. Uses specific temporal models where available,
	 * and falls back to the Unified model for pre-1750 historical prediction.
	 */
	
	static async D_generateMultinomialLogitRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
		
		//Declare local instance variables
		let check_cohort = this.getCohorts()[0];
		let years = landuse_HYDE.sorted_hyde_years;
		
		if (!fs.existsSync(this.intermediate_logit_rasters)) fs.mkdirSync(this.intermediate_logit_rasters, { recursive: true });
		
		let target_years = years.filter((year) => {
			let out_base = `${this.intermediate_logit_rasters}logit_${year}.png`;
			let check_path = out_base.replace(".png", `_class_${check_cohort}.png`);
			return (overwrite || !fs.existsSync(check_path));
		});
		
		if (target_years.length === 0) return [];
		
		//Return statement
		return await Statistics.generateMultinomialRastersParallel(target_years, (year) => {
			let all_keys = Object.keys(this.covariates_obj);
			let covariates_map = {};
			let format_year = year > 2023 ? 2023 : year;
			let model_path = `${this.intermediate_logit_folder}multinomial_model_${year}.json`;
			let out_base = `${this.intermediate_logit_rasters}logit_${year}.png`;
			
			if (year < 1950 || year > 2025 || !fs.existsSync(model_path))
				model_path = `${this.intermediate_logit_folder}multinomial_model_unified.json`;
			
			if (!fs.existsSync(model_path)) return null;
			
			for (let i = 0; i < all_keys.length; i++) {
				let k = all_keys[i];
				let info = this.covariates_obj[k](format_year);
				covariates_map[k] = info;
			}
			
			return {
				covariates_map: covariates_map,
				model_obj: model_path,
				options: {
					format: "float32",
					output_mode: "probabilities"
				},
				output_file_path: out_base
			};
		}, {
			concurrency: options.concurrency,
			name: "Age Sex Multinomial Logit Raster Generation"
		});
	}
	
	/**
	 * Clamps the logit probability fields into exact local population aggregates anchoring perfectly to Stadestér.
	 * Probabilities are normalised per-pixel across all cohorts so that cohort sums exactly equal the Stadestér total.
	 */
	static async E_clampToStadester (arg0_options) {
		let options = (arg0_options) ? arg0_options : {};
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;

		if (!fs.existsSync(this.intermediate_clamped_rasters)) fs.mkdirSync(this.intermediate_clamped_rasters, { recursive: true });
		
		let years = landuse_HYDE.sorted_hyde_years;
		let cohorts = this.getCohorts();
		
		for (let y = 0; y < years.length; y++) {
			let year = years[y];
			let format_year = year > 2023 ? 2023 : year;
			let popc_info = this.covariates_obj["popc_"](format_year);
			
			if (!fs.existsSync(popc_info[0])) continue;
			
			let popc_raster = GeoPNG.loadNumberRasterImage(popc_info[0], { format: popc_info[1] });
			
			//1. Load all cohort probability rasters for the current year upfront
			let prob_rasters = {};
			let missing_probs = false;
			
			for (let i = 0; i < cohorts.length; i++) {
				let prob_path = `${this.intermediate_logit_rasters}logit_${year}_class_${cohorts[i]}.png`;
				
				if (!fs.existsSync(prob_path)) { missing_probs = true; break; }
				prob_rasters[cohorts[i]] = GeoPNG.loadNumberRasterImage(prob_path, { format: "float32" });
			}
			
			if (missing_probs) continue;
			
			//2. Compute per-pixel probability sums for normalisation
			let total_pixels = 4320 * 2160;
			let prob_sums = new Float32Array(total_pixels);
			
			for (let i = 0; i < cohorts.length; i++) {
				let data = prob_rasters[cohorts[i]].data;
				
				for (let j = 0; j < total_pixels; j++) {
					let val = data[j];
					if (!isNaN(val) && val > 0) prob_sums[j] += val;
				}
			}
			
			//3. Distribute normalised probabilities into exact population aggregates
			let has_clamped = false;
			
			for (let i = 0; i < cohorts.length; i++) {
				let c = cohorts[i];
				let out_path = `${this.intermediate_clamped_rasters}global_${c}_${year}.png`;
				
				if (!overwrite && fs.existsSync(out_path)) continue;
				
				let prob_raster = prob_rasters[c];
				
				GeoPNG.saveNumberRasterImage({
					file_path: out_path,
					format: "float32",
					width: 4320,
					height: 2160,
					function: (local_index) => {
						let local_stadester_pop = popc_raster.data[local_index];
						
						//Ocean / Null-Mask Fallback
						if (local_stadester_pop <= 0) return 0;
						
						let local_prob_sum = prob_sums[local_index];
						let local_prob = prob_raster.data[local_index];
						if (isNaN(local_prob) || local_prob < 0) local_prob = 0;
						
						//Uniform Fallback: distribute evenly across cohorts if the model yielded no signal
						if (local_prob_sum <= 0) return local_stadester_pop / cohorts.length;
						
						//Normalised probabilities are distributed exactly across the anchor footprint
						return local_stadester_pop * (local_prob / local_prob_sum);
					}
				});
				
				has_clamped = true;
			}
			
			if (has_clamped) console.log(`Clamped spatial demographic cohort aggregates securely to Stadestér populations for year ${year}.`);
			
			await Blacktraffic.yield();
		}
	}
	
	static async F_compositeTimeseries (arg0_options) {
		let options = (arg0_options) ? arg0_options : {};
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;

		if (!fs.existsSync(this.output_rasters)) fs.mkdirSync(this.output_rasters, { recursive: true });
		
		let cohorts = this.getCohorts();
		let years = landuse_HYDE.sorted_hyde_years;
		
		//Cache the WorldPop directory listing once to avoid repeated disk reads
		let wp_files = [];
		if (fs.existsSync(age_sex_WorldPop.output_rasters)) {
			wp_files = fs.readdirSync(age_sex_WorldPop.output_rasters);
		}
		
		//Iterate over the full temporal domain
		for (let y = 0; y < years.length; y++) {
			let year = years[y];
			let has_composited = false;
			
			for (let c = 0; c < cohorts.length; c++) {
				let cohort = cohorts[c];
				let out_path = `${this.output_rasters}${cohort}_${year}.png`;
				
				if (!overwrite && fs.existsSync(out_path)) continue;
				
				let src_path = null;
				
				//1. UNWPP actuals take precedence for 1950-2014
				if (year >= 1950 && year < 2015) {
					let unwpp_path = `${age_sex_UNWPP.output_clamped_to_stadester}global_${cohort}_${year}.png`;
					if (fs.existsSync(unwpp_path)) src_path = unwpp_path;
				}
				
				//2. WorldPop actuals take precedence for 2015-2025
				if (year >= 2015 && year <= 2025) {
					let regex = new RegExp(`^.*${cohort}_${year}.*\\.png$`);
					let wp_match = wp_files.find(f => regex.test(f));
					
					if (wp_match) {
						src_path = `${age_sex_WorldPop.output_rasters}${wp_match}`;
					} else {
						//Fallback to UNWPP if the specific WorldPop year is missing
						let unwpp_fallback = `${age_sex_UNWPP.output_clamped_to_stadester}global_${cohort}_${year}.png`;
						if (fs.existsSync(unwpp_fallback)) src_path = unwpp_fallback;
					}
				}
				
				//3. Default to the clamped multinomial logit rasters for all other years (pre-1950, post-2025, or missing actuals)
				if (!src_path) {
					let clamped_path = `${this.intermediate_clamped_rasters}global_${cohort}_${year}.png`;
					if (fs.existsSync(clamped_path)) src_path = clamped_path;
				}
				
				if (src_path) {
					fs.copyFileSync(src_path, out_path);
					has_composited = true;
				}
			}
			
			if (has_composited) console.log(`Composited demographic cohort timeseries for year ${year}.`);
			
			await Blacktraffic.yield();
		}
	}
	
	static async processRasters (arg0_options) {
		let options = (arg0_options) ? arg0_options : {};
		if (!options.exclude) options.exclude = [];
		if (options.skip_training || options.use_existing_models || options.train === false) {
			if (!options.exclude.includes("B")) options.exclude.push("B");
			if (!options.exclude.includes("C")) options.exclude.push("C");
			console.log(`[age_sex] Skipping Steps B & C training (using existing models).`);
		}
		
		if (!options.exclude.includes("A")) await this.A_standardiseTargets(options);
		if (!options.exclude.includes("B")) await this.B_trainMultinomialLogitModels(options);
		if (!options.exclude.includes("C")) await this.C_mergeMultinomialLogitModels(options);
		if (!options.exclude.includes("D")) await this.D_generateMultinomialLogitRasters(options);
		if (!options.exclude.includes("E")) await this.E_clampToStadester(options);
		if (!options.exclude.includes("F")) await this.F_compositeTimeseries(options);
	}
};