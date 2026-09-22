/**
 * Raster implementation for the standalone classifier. Kept separate from the
 * statistical model so full-resolution buffers are only allocated when requested.
 *
 * Implements vectorised, allocation-free pixel evaluation and parallel timeseries
 * execution through GeoPNG.processTimeseriesParallel with cooperative yielding.
 */
global.age_sex_classifier_rasters = class {
	/**
	 * Loads trained stage models defined in the classifier manifest.
	 * @alias age_sex_classifier_rasters._loadModels
	 *
	 * @param {Object} arg0_manifest
	 *
	 * @returns {Object} Map of stage keys to parsed model objects.
	 */
	static _loadModels (arg0_manifest) {
		//Convert from parameters
		let manifest = (arg0_manifest) ? arg0_manifest : {};

		//Declare local instance variables
		let models = {};
		let model_entries = manifest.models || [];

		//Function body
		for (let i = 0; i < model_entries.length; i++) {
			let entry = model_entries[i];
			if (fs.existsSync(entry.path))
				models[entry.stage] = JSON.parse(fs.readFileSync(entry.path, "utf8"));
		}

		//Return statement
		return models;
	}

	/**
	 * Builds a string-keyed colour lookup table. Maintained for backward compatibility.
	 * @alias age_sex_classifier_rasters._modernColourLookup
	 *
	 * @returns {Object} Map of "r,g,b" to ISO3 geocode.
	 */
	static _modernColourLookup () {
		//Declare local instance variables
		let lookup = {};
		let source = admin_modern.getISO3ColourcodesObject();

		//Function body
		Object.iterate(source, (colour, geocodes) => {
			if (geocodes.length > 0) lookup[colour] = geocodes[0];
		});

		//Return statement
		return lookup;
	}

	/**
	 * Builds a packed 24-bit integer colour lookup Map ((r << 16) | (g << 8) | b) -> geocode.
	 * Avoids string allocations during pixel iteration.
	 * @alias age_sex_classifier_rasters._modernColourLookupPacked
	 *
	 * @returns {Map<number, string>}
	 */
	static _modernColourLookupPacked () {
		//Declare local instance variables
		let lookup = new Map();
		let source = admin_modern.getISO3ColourcodesObject();

		//Function body
		Object.iterate(source, (colour, geocodes) => {
			if (geocodes.length > 0) {
				let parts = colour.split(",");
				if (parts.length >= 3) {
					let packed_key = (Number(parts[0]) << 16) | (Number(parts[1]) << 8) | Number(parts[2]);
					lookup.set(packed_key, geocodes[0]);
				}
			}
		});

		//Return statement
		return lookup;
	}

	/**
	 * Pre-compiles stage multinomial models into flattened Float64Arrays for zero-allocation dot products.
	 * @alias age_sex_classifier_rasters._compileStageModels
	 *
	 * @param {Object} arg0_models
	 * @param {Array<string>} arg1_cohorts
	 * @param {Array<string>} arg2_keys
	 *
	 * @returns {Object} Map of stage keys to { intercepts: Float64Array, weights: Float64Array }.
	 */
	static _compileStageModels (arg0_models, arg1_cohorts, arg2_keys) {
		//Convert from parameters
		let models = (arg0_models) ? arg0_models : {};
		let cohorts = (arg1_cohorts) ? arg1_cohorts : [];
		let keys = (arg2_keys) ? arg2_keys : [];

		//Declare local instance variables
		let compiled = {};
		let num_classes = cohorts.length;
		let num_keys = keys.length;

		//Function body
		Object.iterate(models, (stage, model) => {
			let intercepts = new Float64Array(num_classes);
			let weights = new Float64Array(num_classes*num_keys);

			for (let c = 0; c < num_classes; c++) {
				let coef = model.coefficients?.[cohorts[c]];
				if (coef) {
					intercepts[c] = coef._intercept || 0;
					for (let k = 0; k < num_keys; k++)
						weights[c*num_keys + k] = coef[keys[k]] || 0;
				}
			}

			compiled[stage] = { intercepts: intercepts, weights: weights };
		});

		//Return statement
		return compiled;
	}

	/**
	 * Computes pixel features as an object. Retained for external compatibility and testing.
	 * @alias age_sex_classifier_rasters._pixelFeatures
	 *
	 * @param {number} arg0_index
	 * @param {Array<string>} arg1_keys
	 * @param {Object} arg2_rasters
	 * @param {number|string} arg3_year
	 *
	 * @returns {Object}
	 */
	static _pixelFeatures (arg0_index, arg1_keys, arg2_rasters, arg3_year) {
		//Convert from parameters
		let index = arg0_index;
		let keys = (arg1_keys) ? arg1_keys : [];
		let rasters = (arg2_rasters) ? arg2_rasters : {};
		let year = arg3_year;

		//Declare local instance variables
		let features = {};

		//Function body
		for (let k = 0; k < keys.length; k++) {
			let key = keys[k];
			if (rasters[key]) features[key] = Number(rasters[key].data[index]) || 0;
		}

		let popc = features.popc_ || 0;
		if (keys.includes("urban_share"))
			features.urban_share = popc > 0 ? (features.urbc_ || 0)/popc : 0;
		if (keys.includes("log_population_density"))
			features.log_population_density = Math.log(Math.max(0.01, features.popd_ || 0));
		if (keys.includes("log_gdp_ppp_pc"))
			features.log_gdp_ppp_pc = Math.log(Math.max(1, features.gdp_ppp_pc || 0));
		if (keys.includes("year_scaled"))
			features.year_scaled = Number(year)/1000;

		//Return statement
		return features;
	}

	/**
	 * Generates M1 multinomial mixture rasters for a single year using vectorised typed array operations.
	 * @alias age_sex_classifier_rasters.generateM1Year
	 *
	 * @param {Object} arg0_classifier
	 * @param {number|string} arg1_year
	 * @param {Object} [arg2_options]
	 *
	 * @returns {Promise<{year: number, stages: Array<string>, success: boolean}>}
	 */
	static async generateM1Year (arg0_classifier, arg1_year, arg2_options) {
		//Convert from parameters
		let classifier = arg0_classifier;
		let year = Number(arg1_year);
		let options = (arg2_options) ? arg2_options : {};

		//Declare local instance variables
		let all_weights = options.weights || JSON.parse(fs.readFileSync(classifier.weights_file, "utf8"));
		let cohorts = classifier.getCohorts();
		let colour_lookup = this._modernColourLookupPacked();
		let format_year = year > 2023 ? 2023 : year;
		let geocode_raster = GeoPNG.loadImage(options.geocode_raster_path || admin_modern.input_geocodes_raster);
		let manifest = options.manifest || JSON.parse(fs.readFileSync(classifier.manifest_file, "utf8"));
		let models = this._loadModels(manifest);
		let stages = age_sex_classifier_demography.stages.filter((stage) => models[stage]);

		let height = geocode_raster.height;
		let width = geocode_raster.width;
		let total_pixels = width*height;
		let geocode_data = geocode_raster.data;

		let keys = Array.from(new Set(Object.values(models).flatMap((model) => model.covariates || [])));
		let num_classes = cohorts.length;
		let num_keys = keys.length;

		let raster_keys = new Set(keys);
		if (keys.includes("urban_share")) raster_keys.add("urbc_").add("popc_");
		if (keys.includes("log_population_density")) raster_keys.add("popd_");
		if (keys.includes("log_gdp_ppp_pc")) raster_keys.add("gdp_ppp_pc");

		let rasters = {};
		for (let key of raster_keys) {
			if (["urban_share", "log_population_density", "log_gdp_ppp_pc", "year_scaled"].includes(key)) continue;
			let info = classifier.covariates_obj[key]?.(format_year);
			if (info && fs.existsSync(info[0]))
				rasters[key] = GeoPNG.loadNumberRasterImage(info[0], { format: info[1] || "float32" });
		}

		//Compile models into flat Float64Arrays
		let compiled_models = this._compileStageModels(models, cohorts, keys);

		//Set up direct raster buffers for zero-allocation feature extraction
		let direct_rasters = [];
		for (let k = 0; k < num_keys; k++) {
			let key = keys[k];
			if (!["urban_share", "log_population_density", "log_gdp_ppp_pc", "year_scaled"].includes(key) && rasters[key]) {
				direct_rasters.push({
					data: rasters[key].data,
					feature_index: k
				});
			}
		}

		let has_log_gdp = keys.includes("log_gdp_ppp_pc");
		let has_log_popd = keys.includes("log_population_density");
		let has_urban_share = keys.includes("urban_share");
		let has_year_scaled = keys.includes("year_scaled");

		let gdp_data = rasters.gdp_ppp_pc?.data;
		let log_gdp_index = keys.indexOf("log_gdp_ppp_pc");
		let log_popd_index = keys.indexOf("log_population_density");
		let popc_data = rasters.popc_?.data;
		let popd_data = rasters.popd_?.data;
		let urbc_data = rasters.urbc_?.data;
		let urban_share_index = keys.indexOf("urban_share");
		let year_scaled_index = keys.indexOf("year_scaled");
		let year_scaled_value = year/1000;

		//Allocate reusable pixel buffers and output layers
		let blended_probs = new Float64Array(num_classes);
		let feature_buf = new Float64Array(num_keys);
		let outputs = cohorts.map(() => new Float32Array(total_pixels));
		let stage_logits = new Float64Array(num_classes);
		let stage_probs = new Float64Array(num_classes);
		let weight_cache = new Map();

		if (has_year_scaled) feature_buf[year_scaled_index] = year_scaled_value;

		//Main pixel loop with row-level event loop yielding
		for (let y = 0; y < height; y++) {
			let row_offset = y*width;

			for (let x = 0; x < width; x++) {
				let i = row_offset + x;
				let i4 = i*4;

				let packed_colour = (geocode_data[i4] << 16) | (geocode_data[i4 + 1] << 8) | geocode_data[i4 + 2];
				if (packed_colour === 0) continue;

				let geocode = colour_lookup.get(packed_colour);
				if (!geocode) continue;

				//Extract features directly into typed buffer without allocation
				for (let d = 0; d < direct_rasters.length; d++)
					feature_buf[direct_rasters[d].feature_index] = direct_rasters[d].data[i] || 0;

				if (has_urban_share) {
					let popc = popc_data ? popc_data[i] : 0;
					let urbc = urbc_data ? urbc_data[i] : 0;
					feature_buf[urban_share_index] = popc > 0 ? urbc/popc : 0;
				}
				if (has_log_popd) {
					let popd = popd_data ? popd_data[i] : 0;
					feature_buf[log_popd_index] = Math.log(Math.max(0.01, popd));
				}
				if (has_log_gdp) {
					let gdp = gdp_data ? gdp_data[i] : 0;
					feature_buf[log_gdp_index] = Math.log(Math.max(1, gdp));
				}

				//Retrieve or compile active stages for this geocode
				let weight_entry = weight_cache.get(geocode);
				if (!weight_entry) {
					let resolved_weights = classifier._resolveWeights(all_weights, geocode, year);
					let active_stages = [];
					let total_weight = 0;

					for (let s = 0; s < stages.length; s++) {
						let stage = stages[s];
						let w = Math.max(0, classifier._safeNumber(resolved_weights[stage], 0));
						if (w > 0 && compiled_models[stage]) {
							active_stages.push({
								compiled: compiled_models[stage],
								weight: w
							});
							total_weight += w;
						}
					}

					weight_entry = {
						active_stages: active_stages,
						total_weight: total_weight
					};
					weight_cache.set(geocode, weight_entry);
				}

				let active_stages = weight_entry.active_stages;
				let total_weight = weight_entry.total_weight;

				if (active_stages.length === 0 || total_weight <= 0) {
					let uniform = 1/num_classes;
					for (let c = 0; c < num_classes; c++) outputs[c][i] = uniform;
					continue;
				}

				//Vectorised softmax evaluation and archetype blending
				for (let c = 0; c < num_classes; c++) blended_probs[c] = 0;

				for (let s = 0; s < active_stages.length; s++) {
					let active_stage = active_stages[s];
					let intercepts = active_stage.compiled.intercepts;
					let max_logit = -Infinity;
					let model_weights = active_stage.compiled.weights;

					for (let c = 0; c < num_classes; c++) {
						let offset = c*num_keys;
						let logit = intercepts[c];
						for (let k = 0; k < num_keys; k++)
							logit += feature_buf[k]*model_weights[offset + k];
						stage_logits[c] = logit;
						if (logit > max_logit) max_logit = logit;
					}

					let sum_exp = 0;
					for (let c = 0; c < num_classes; c++) {
						let exp_val = Math.exp(stage_logits[c] - max_logit);
						stage_probs[c] = exp_val;
						sum_exp += exp_val;
					}

					let inv_sum = sum_exp > 0 ? 1/sum_exp : 0;
					let stage_weight = active_stage.weight;
					for (let c = 0; c < num_classes; c++)
						blended_probs[c] += stage_weight*(stage_probs[c]*inv_sum);
				}

				let blended_sum = 0;
				for (let c = 0; c < num_classes; c++) blended_sum += blended_probs[c];
				let inv_total = blended_sum > 0 ? 1/blended_sum : (1/num_classes);

				for (let c = 0; c < num_classes; c++)
					outputs[c][i] = blended_probs[c]*inv_total;
			}

			//Cooperative yield every 100 rows to maintain UI responsiveness and stream logs
			if (y % 100 === 0 && typeof Blacktraffic !== "undefined" && Blacktraffic.yield)
				await Blacktraffic.yield(0);
		}

		//Save M1 probability rasters asynchronously
		fs.mkdirSync(classifier.m1_rasters, { recursive: true });
		for (let c = 0; c < cohorts.length; c++) {
			await GeoPNG.saveNumberRasterImageAsync({
				data: outputs[c],
				file_path: `${classifier.m1_rasters}m1_${year}_class_${cohorts[c]}.png`,
				format: "float32",
				height: height,
				width: width
			});
		}

		//Return statement
		return { year: year, stages: stages, success: true };
	}

	/**
	 * Parallel runner for M1 raster generation across all HYDE years.
	 * @alias age_sex_classifier_rasters.generateM1
	 *
	 * @param {Object} arg0_classifier
	 * @param {Object} [arg1_options]
	 *  @param {number} [arg1_options.concurrency=4]
	 *  @param {Array<number>} [arg1_options.years]
	 *
	 * @returns {Promise<Array<Object>>}
	 */
	static async generateM1 (arg0_classifier, arg1_options) {
		//Convert from parameters
		let classifier = arg0_classifier;
		let options = (arg1_options) ? arg1_options : {};

		//Declare local instance variables
		let years = options.raster_years || options.years ||
			((typeof classifier.getHYDEYears === "function") ? classifier.getHYDEYears() :
			((typeof landuse_HYDE !== "undefined") ? landuse_HYDE.sorted_hyde_years : []));

		//Function body
		let results = await GeoPNG.processTimeseriesParallel({
			concurrency: options.concurrency || 4,
			handler: async (year) => {
				return await this.generateM1Year(classifier, year, options);
			},
			items: years,
			name: "M1 Raster Generation",
			use_workers: false
		});

		//Return statement
		return results;
	}

	/**
	 * Checks whether all specified file paths exist synchronously.
	 * @alias age_sex_classifier_rasters._allFilesExist
	 *
	 * @param {Array<string>} arg0_paths
	 *
	 * @returns {boolean}
	 */
	static _allFilesExist (arg0_paths) {
		//Convert from parameters
		let paths = (arg0_paths) ? arg0_paths : [];

		//Function body
		for (let i = 0; i < paths.length; i++)
			if (!fs.existsSync(paths[i])) return false;

		//Return statement
		return true;
	}

	/**
	 * Copies empirical UNWPP cohort rasters directly if present for modern years.
	 * @alias age_sex_classifier_rasters._copyEmpiricalYear
	 *
	 * @param {Object} arg0_classifier
	 * @param {number|string} arg1_year
	 * @param {Array<string>} arg2_cohorts
	 *
	 * @returns {Promise<boolean>}
	 */
	static async _copyEmpiricalYear (arg0_classifier, arg1_year, arg2_cohorts) {
		//Convert from parameters
		let classifier = arg0_classifier;
		let year = Number(arg1_year);
		let cohorts = (arg2_cohorts) ? arg2_cohorts : [];

		//Guard clauses
		if (year < 1950 || typeof age_sex_UNWPP === "undefined") return false;

		//Declare local instance variables
		let paths = cohorts.map((cohort) => `${age_sex_UNWPP.output_clamped_to_stadester}global_${cohort}_${year}.png`);

		if (!this._allFilesExist(paths)) return false;

		//Function body
		fs.mkdirSync(classifier.m2_rasters, { recursive: true });
		fs.mkdirSync(classifier.output_rasters, { recursive: true });

		let publish_to_production = (options.publish === true || options.export_to_production === true || options.export_to_age_sex === true);
		if (publish_to_production && typeof age_sex !== "undefined" && age_sex.output_rasters)
			fs.mkdirSync(age_sex.output_rasters, { recursive: true });

		for (let c = 0; c < cohorts.length; c++) {
			let m2_path = `${classifier.m2_rasters}global_${cohorts[c]}_${year}.png`;
			fs.copyFileSync(paths[c], m2_path);
			fs.copyFileSync(paths[c], `${classifier.output_rasters}${cohorts[c]}_${year}.png`);
			fs.copyFileSync(paths[c], `${classifier.output_rasters}global_${cohorts[c]}_${year}.png`);

			if (publish_to_production && typeof age_sex !== "undefined" && age_sex.output_rasters)
				fs.copyFileSync(paths[c], `${age_sex.output_rasters}${cohorts[c]}_${year}.png`);
		}

		//Return statement
		return true;
	}

	/**
	 * Applies M2 shocks, blends empirical observations and saves composited rasters for a single year.
	 * @alias age_sex_classifier_rasters.applyM2Year
	 *
	 * @param {Object} arg0_classifier
	 * @param {number|string} arg1_year
	 * @param {Object} [arg2_options]
	 *
	 * @returns {Promise<{year: number, empirical: string|null, pava: boolean, success: boolean}>}
	 */
	static async applyM2Year (arg0_classifier, arg1_year, arg2_options) {
		//Convert from parameters
		let classifier = arg0_classifier;
		let year = Number(arg1_year);
		let options = (arg2_options) ? arg2_options : {};

		//Declare local instance variables
		let cohorts = classifier.getCohorts();
		let num_cohorts = cohorts.length;

		//1. Check empirical UNWPP fallback
		if (await this._copyEmpiricalYear(classifier, year, cohorts))
			return { year: year, empirical: "UNWPP", success: true };

		//2. Verify probability raster presence
		let probability_paths = cohorts.map((cohort) => `${classifier.m1_rasters}m1_${year}_class_${cohort}.png`);
		if (!this._allFilesExist(probability_paths)) return { year: year, success: false };

		let probability_rasters = probability_paths.map((file_path) =>
			GeoPNG.loadNumberRasterImage(file_path, { format: "float32" })
		);

		let format_year = year > 2023 ? 2023 : year;
		let pop_info = classifier.covariates_obj.popc_?.(format_year);
		if (!pop_info || !fs.existsSync(pop_info[0])) return { year: year, success: false };

		let population_raster = GeoPNG.loadNumberRasterImage(pop_info[0], { format: pop_info[1] || "float32" });
		let modern_raster = GeoPNG.loadImage(admin_modern.input_geocodes_raster);
		let modern_lookup = this._modernColourLookupPacked();

		//3. HMD historical empirical masks
		let has_hmd = (year < 1950 && typeof age_sex_HMD !== "undefined");
		let hmd_target_data = has_hmd && typeof age_sex_HMD.A_getHMDObject === "function" ?
			age_sex_HMD.A_getHMDObject() : {};
		let hmd_lookup = has_hmd ? classifier._buildHMDColourLookup(year, hmd_target_data) : {};
		let hmd_raster = (has_hmd && admin_modern.input_hmd_raster && fs.existsSync(admin_modern.input_hmd_raster)) ?
			GeoPNG.loadImage(admin_modern.input_hmd_raster) : null;
		let hmd_paths = (has_hmd && age_sex_HMD.output_clamped_to_stadester) ?
			cohorts.map((cohort) => `${age_sex_HMD.output_clamped_to_stadester}global_${cohort}_${year}.png`) : [];
		let hmd_cohorts = (hmd_paths.length > 0 && this._allFilesExist(hmd_paths)) ?
			hmd_paths.map((file_path) => GeoPNG.loadNumberRasterImage(file_path, { format: "float32" })) : null;

		let hmd_packed_set = new Set();
		if (hmd_raster && hmd_cohorts) {
			Object.iterate(hmd_lookup, (colour) => {
				let parts = colour.split(",");
				if (parts.length >= 3)
					hmd_packed_set.add((Number(parts[0]) << 16) | (Number(parts[1]) << 8) | Number(parts[2]));
			});
		}

		//4. Catalogues and pre-filtered active shocks
		let catalogues = classifier.loadM2Catalogues();
		let shock_cache = new Map();

		let height = population_raster.height;
		let width = population_raster.width;
		let total_pixels = width*height;
		let modern_data = modern_raster.data;
		let hmd_data = hmd_raster ? hmd_raster.data : null;
		let pop_data = population_raster.data;

		let counts_buf = new Float64Array(num_cohorts);
		let outputs = cohorts.map(() => new Float32Array(total_pixels));

		//Main pixel loop with row-level event loop yielding
		for (let y = 0; y < height; y++) {
			let row_offset = y*width;

			for (let x = 0; x < width; x++) {
				let i = row_offset + x;
				let population = Number(pop_data[i]) || 0;
				if (population <= 0) continue;

				let i4 = i*4;
				let modern_colour = (modern_data[i4] << 16) | (modern_data[i4 + 1] << 8) | modern_data[i4 + 2];
				if (modern_colour === 0) continue;

				let geocode = modern_lookup.get(modern_colour);
				if (!geocode) continue;

				let empirical = false;
				if (hmd_data && hmd_cohorts) {
					let hmd_colour = (hmd_data[i4] << 16) | (hmd_data[i4 + 1] << 8) | hmd_data[i4 + 2];
					empirical = hmd_packed_set.has(hmd_colour);
				}

				if (empirical) {
					for (let c = 0; c < num_cohorts; c++)
						outputs[c][i] = Number(hmd_cohorts[c].data[i]) || 0;
					continue;
				}

				//Check if this geocode has active shocks in this year
				let has_shocks = shock_cache.get(geocode);
				if (has_shocks === undefined) {
					let found_shock = false;
					let ordered_types = ["fertility", "mortality", "migration"];
					for (let t = 0; t < ordered_types.length; t++) {
						let shocks = catalogues[ordered_types[t]]?.shocks || [];
						for (let s = 0; s < shocks.length; s++) {
							if (Number(year) >= Number(shocks[s].start_year) &&
									age_sex_classifier_shocks._appliesToGeocode(shocks[s], geocode)) {
								found_shock = true;
								break;
							}
						}
						if (found_shock) break;
					}
					has_shocks = found_shock;
					shock_cache.set(geocode, has_shocks);
				}

				if (!has_shocks) {
					//Fast path: zero shocks, direct multiplication without function calls
					for (let c = 0; c < num_cohorts; c++)
						outputs[c][i] = Math.max(0, Number(probability_rasters[c].data[i]) || 0)*population;
				} else {
					//Slow path: apply shocks to reusable buffer
					for (let c = 0; c < num_cohorts; c++)
						counts_buf[c] = Math.max(0, Number(probability_rasters[c].data[i]) || 0)*population;

					age_sex_classifier_shocks.applyShocksToBuffer(counts_buf, cohorts, {
						catalogues: catalogues,
						empirical_available: false,
						geocode: geocode,
						year: year
					});

					for (let c = 0; c < num_cohorts; c++)
						outputs[c][i] = counts_buf[c];
				}
			}

			//Cooperative yield every 100 rows to maintain UI responsiveness and stream logs
			if (y % 100 === 0 && typeof Blacktraffic !== "undefined" && Blacktraffic.yield)
				await Blacktraffic.yield(0);
		}

		//Save composited M2 outputs asynchronously
		fs.mkdirSync(classifier.m2_rasters, { recursive: true });
		fs.mkdirSync(classifier.output_rasters, { recursive: true });

		let publish_to_production = (options.publish === true || options.export_to_production === true || options.export_to_age_sex === true);
		if (publish_to_production && typeof age_sex !== "undefined" && age_sex.output_rasters)
			fs.mkdirSync(age_sex.output_rasters, { recursive: true });

		for (let c = 0; c < num_cohorts; c++) {
			let m2_path = `${classifier.m2_rasters}global_${cohorts[c]}_${year}.png`;
			await GeoPNG.saveNumberRasterImageAsync({
				data: outputs[c],
				file_path: m2_path,
				format: "float32",
				height: height,
				width: width
			});
			fs.copyFileSync(m2_path, `${classifier.output_rasters}${cohorts[c]}_${year}.png`);
			fs.copyFileSync(m2_path, `${classifier.output_rasters}global_${cohorts[c]}_${year}.png`);

			if (publish_to_production && typeof age_sex !== "undefined" && age_sex.output_rasters)
				fs.copyFileSync(m2_path, `${age_sex.output_rasters}${cohorts[c]}_${year}.png`);
		}

		//Return statement
		return { year: year, empirical: hmd_cohorts ? "HMD masks" : null, pava: false, success: true };
	}

	/**
	 * Parallel runner for M2 prior application and compositing across all HYDE years.
	 * @alias age_sex_classifier_rasters.applyM2
	 *
	 * @param {Object} arg0_classifier
	 * @param {Object} [arg1_options]
	 *  @param {number} [arg1_options.concurrency=4]
	 *  @param {Array<number>} [arg1_options.years]
	 *
	 * @returns {Promise<Array<Object>>}
	 */
	static async applyM2 (arg0_classifier, arg1_options) {
		//Convert from parameters
		let classifier = arg0_classifier;
		let options = (arg1_options) ? arg1_options : {};

		//Declare local instance variables
		let years = options.raster_years || options.years ||
			((typeof classifier.getHYDEYears === "function") ? classifier.getHYDEYears() :
			((typeof landuse_HYDE !== "undefined") ? landuse_HYDE.sorted_hyde_years : []));

		//Function body
		let results = await GeoPNG.processTimeseriesParallel({
			concurrency: options.concurrency || 4,
			handler: async (year) => {
				return await this.applyM2Year(classifier, year, options);
			},
			items: years,
			name: "M2 Prior Application & Compositing",
			use_workers: false
		});

		//Return statement
		return results;
	}
};
