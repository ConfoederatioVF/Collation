/**
 * Raster implementation for the standalone classifier. Kept separate from the
 * statistical model so full-resolution buffers are only allocated when requested.
 */
global.age_sex_classifier_rasters = class {
	static _loadModels (arg0_manifest) {
		let models = {};
		for (let i = 0; i < (arg0_manifest.models || []).length; i++) {
			let entry = arg0_manifest.models[i];
			if (fs.existsSync(entry.path)) models[entry.stage] = JSON.parse(fs.readFileSync(entry.path, "utf8"));
		}
		return models;
	}

	static _modernColourLookup () {
		let source = admin_modern.getISO3ColourcodesObject();
		let lookup = {};
		Object.iterate(source, (colour, geocodes) => {
			if (geocodes.length > 0) lookup[colour] = geocodes[0];
		});
		return lookup;
	}

	static _pixelFeatures (arg0_index, arg1_keys, arg2_rasters, arg3_year) {
		let features = {};
		for (let k = 0; k < arg1_keys.length; k++) {
			let key = arg1_keys[k];
			if (arg2_rasters[key]) features[key] = Number(arg2_rasters[key].data[arg0_index]) || 0;
		}
		let popc = features.popc_ || 0;
		if (arg1_keys.includes("urban_share"))
			features.urban_share = popc > 0 ? (features.urbc_ || 0)/popc : 0;
		if (arg1_keys.includes("log_population_density"))
			features.log_population_density = Math.log(Math.max(0.01, features.popd_ || 0));
		if (arg1_keys.includes("log_gdp_ppp_pc"))
			features.log_gdp_ppp_pc = Math.log(Math.max(1, features.gdp_ppp_pc || 0));
		if (arg1_keys.includes("year_scaled")) features.year_scaled = Number(arg3_year)/1000;
		return features;
	}

	static async generateM1Year (arg0_classifier, arg1_year, arg2_options) {
		let classifier = arg0_classifier;
		let year = Number(arg1_year);
		let options = arg2_options || {};
		let manifest = options.manifest || JSON.parse(fs.readFileSync(classifier.manifest_file, "utf8"));
		let all_weights = options.weights || JSON.parse(fs.readFileSync(classifier.weights_file, "utf8"));
		let models = this._loadModels(manifest);
		let cohorts = classifier.getCohorts();
		let keys = Array.from(new Set(Object.values(models).flatMap((model) => model.covariates || [])));
		let format_year = year > 2023 ? 2023 : year;
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
		let geocode_raster = GeoPNG.loadImage(options.geocode_raster_path || admin_modern.input_geocodes_raster);
		let colour_lookup = this._modernColourLookup();
		let width = geocode_raster.width;
		let height = geocode_raster.height;
		let pixels = width*height;
		let outputs = cohorts.map(() => new Float32Array(pixels));
		let stages = age_sex_classifier_demography.stages.filter((stage) => models[stage]);
		let weight_cache = {};

		for (let i = 0; i < pixels; i++) {
			let colour = `${geocode_raster.data[i*4]},${geocode_raster.data[i*4 + 1]},${geocode_raster.data[i*4 + 2]}`;
			let geocode = colour_lookup[colour];
			if (!geocode) continue;
			let features = this._pixelFeatures(i, keys, rasters, year);
			let stage_weights = weight_cache[geocode] ||
				(weight_cache[geocode] = classifier._resolveWeights(all_weights, geocode, year));
			let probabilities = classifier.predictM1(features, stage_weights, models);
			for (let c = 0; c < cohorts.length; c++) outputs[c][i] = probabilities[cohorts[c]] || 0;
		}

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
		return { year: year, stages: stages, success: true };
	}

	static async generateM1 (arg0_classifier, arg1_options) {
		let classifier = arg0_classifier;
		let options = arg1_options || {};
		let years = options.years || landuse_HYDE.sorted_hyde_years;
		let results = [];
		for (let i = 0; i < years.length; i++)
			results.push(await this.generateM1Year(classifier, years[i], options));
		return results;
	}

	static _allFilesExist (arg0_paths) {
		for (let i = 0; i < arg0_paths.length; i++)
			if (!fs.existsSync(arg0_paths[i])) return false;
		return true;
	}

	static async _copyEmpiricalYear (arg0_classifier, arg1_year, arg2_cohorts) {
		let classifier = arg0_classifier;
		let year = Number(arg1_year);
		let cohorts = arg2_cohorts;
		if (year < 1950 || typeof age_sex_UNWPP === "undefined") return false;
		let paths = cohorts.map((cohort) => `${age_sex_UNWPP.output_clamped_to_stadester}global_${cohort}_${year}.png`);
		if (!this._allFilesExist(paths)) return false;
		fs.mkdirSync(classifier.m2_rasters, { recursive: true });
		fs.mkdirSync(classifier.output_rasters, { recursive: true });
		for (let c = 0; c < cohorts.length; c++) {
			fs.copyFileSync(paths[c], `${classifier.m2_rasters}global_${cohorts[c]}_${year}.png`);
			fs.copyFileSync(paths[c], `${classifier.output_rasters}global_${cohorts[c]}_${year}.png`);
		}
		return true;
	}

	static async applyM2Year (arg0_classifier, arg1_year, arg2_options) {
		let classifier = arg0_classifier;
		let year = Number(arg1_year);
		let options = arg2_options || {};
		let cohorts = classifier.getCohorts();
		if (await this._copyEmpiricalYear(classifier, year, cohorts))
			return { year: year, empirical: "UNWPP", success: true };

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
		let modern_lookup = this._modernColourLookup();
		let hmd_target_data = year < 1950 ? age_sex_HMD.A_getHMDObject() : {};
		let hmd_lookup = year < 1950 ? classifier._buildHMDColourLookup(year, hmd_target_data) : {};
		let hmd_raster = year < 1950 ? GeoPNG.loadImage(admin_modern.input_hmd_raster) : null;
		let hmd_paths = cohorts.map((cohort) => `${age_sex_HMD.output_clamped_to_stadester}global_${cohort}_${year}.png`);
		let hmd_cohorts = this._allFilesExist(hmd_paths) ?
			hmd_paths.map((file_path) => GeoPNG.loadNumberRasterImage(file_path, { format: "float32" })) : null;
		let catalogues = classifier.loadM2Catalogues();
		let width = population_raster.width;
		let height = population_raster.height;
		let pixels = width*height;
		let outputs = cohorts.map(() => new Float32Array(pixels));

		for (let i = 0; i < pixels; i++) {
			let population = Number(population_raster.data[i]) || 0;
			if (population <= 0) continue;
			let modern_colour = `${modern_raster.data[i*4]},${modern_raster.data[i*4 + 1]},${modern_raster.data[i*4 + 2]}`;
			let geocode = modern_lookup[modern_colour];
			if (!geocode) continue;
			let empirical = false;
			if (hmd_raster && hmd_cohorts) {
				let hmd_colour = `${hmd_raster.data[i*4]},${hmd_raster.data[i*4 + 1]},${hmd_raster.data[i*4 + 2]}`;
				empirical = !!hmd_lookup[hmd_colour];
			}
			let counts = {};
			for (let c = 0; c < cohorts.length; c++)
				counts[cohorts[c]] = empirical ?
					(Number(hmd_cohorts[c].data[i]) || 0) :
					Math.max(0, Number(probability_rasters[c].data[i]) || 0)*population;
			let adjusted = classifier.applyM2(counts, {
				catalogues: catalogues,
				empirical_available: empirical,
				geocode: geocode,
				year: year
			});
			for (let c = 0; c < cohorts.length; c++) outputs[c][i] = adjusted[cohorts[c]] || 0;
		}

		fs.mkdirSync(classifier.m2_rasters, { recursive: true });
		fs.mkdirSync(classifier.output_rasters, { recursive: true });
		for (let c = 0; c < cohorts.length; c++) {
			let m2_path = `${classifier.m2_rasters}global_${cohorts[c]}_${year}.png`;
			await GeoPNG.saveNumberRasterImageAsync({
				data: outputs[c],
				file_path: m2_path,
				format: "float32",
				height: height,
				width: width
			});
			fs.copyFileSync(m2_path, `${classifier.output_rasters}global_${cohorts[c]}_${year}.png`);
		}
		return { year: year, empirical: hmd_cohorts ? "HMD masks" : null, pava: false, success: true };
	}

	static async applyM2 (arg0_classifier, arg1_options) {
		let classifier = arg0_classifier;
		let options = arg1_options || {};
		let years = options.years || landuse_HYDE.sorted_hyde_years;
		let results = [];
		for (let i = 0; i < years.length; i++)
			results.push(await this.applyM2Year(classifier, years[i], options));
		return results;
	}
};
