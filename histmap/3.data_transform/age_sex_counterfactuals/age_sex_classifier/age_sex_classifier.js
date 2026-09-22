/**
 * Standalone two-pass age/sex classifier.
 *
 * M1 fits population-weighted CDT1-CDT5 multinomial archetypes and mixes them
 * with a phase-constrained Gaussian Bayes classifier. M2 applies static,
 * source-backed fertility, mortality and migration priors. PAVA is not used.
 */
global.age_sex_classifier = class {
	static bf = `${h3}/age_sex_counterfactuals/age_sex_classifier/`;
	static config_file = `${this.bf}classifier_config.json5`;
	static fertility_shocks_file = `${this.bf}M2_fertility.json5`;
	static mortality_shocks_file = `${this.bf}M2_mortality.json5`;
	static migration_shocks_file = `${this.bf}M2_migration.json5`;
	static training_dataset_file = `${this.bf}0.training/training_dataset.json`;
	static archetype_folder = `${this.bf}1.archetype_models/`;
	static stage_model_file = `${this.archetype_folder}M1_stage_classifier.json`;
	static manifest_file = `${this.archetype_folder}M1_classifier.json`;
	static weights_file = `${this.bf}2.m1_weights/M1_weights.json`;
	static m1_rasters = `${this.bf}3.m1_rasters/`;
	static m2_rasters = `${this.bf}4.m2_clamped/`;
	static output_rasters = `${this.bf}5.composite_cohorts/`;

	static get covariates_obj () {
		return (typeof age_sex !== "undefined" && age_sex.covariates_obj) ? age_sex.covariates_obj : {};
	}

	static getCohorts () {
		if (typeof age_sex !== "undefined" && age_sex.getCohorts) return age_sex.getCohorts();
		let cohorts = [];
		let ages = ["00", "01"];
		for (let age = 5; age <= 80; age += 5) ages.push(String(age).padStart(2, "0"));
		for (let i = 0; i < ages.length; i++) cohorts.push(`f_${ages[i]}`, `m_${ages[i]}`);
		return cohorts;
	}

	/**
	 * Returns the sorted canonical HYDE timeseries years spanning 10000 BC (-10000) to 2025 AD.
	 * @alias age_sex_classifier.getHYDEYears
	 *
	 * @returns {Array<number>}
	 */
	static getHYDEYears () {
		if (typeof landuse_HYDE !== "undefined" && Array.isArray(landuse_HYDE.sorted_hyde_years))
			return landuse_HYDE.sorted_hyde_years;

		let years = [
			-10000, -9000, -8000, -7000, -6000, -5000, -4000, -3000, -2000, -1000,
			0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700,
			1710, 1720, 1730, 1740, 1750, 1760, 1770, 1780, 1790, 1800, 1810, 1820, 1830, 1840, 1850, 1860, 1870, 1880, 1890, 1900, 1910, 1920, 1930, 1940, 1950,
			1951, 1952, 1953, 1954, 1955, 1956, 1957, 1958, 1959, 1960, 1961, 1962, 1963, 1964, 1965, 1966, 1967, 1968, 1969, 1970, 1971, 1972, 1973, 1974, 1975, 1976, 1977, 1978, 1979, 1980, 1981, 1982, 1983, 1984, 1985, 1986, 1987, 1988, 1989, 1990, 1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025
		];
		return years.sort((a, b) => a - b);
	}

	static getConfig () {
		if (this._config) return this._config;
		let defaults = {
			training_years: [1850, 1870, 1890, 1910, 1930, 1940, 1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020],
			covariates: ["gdp_pc", "gdp_ppp_pc", "popd_", "urbc_", "rurc_", "delta_popc_", "delta_gdp_pc", "cropland", "pasture"],
			max_iterations: 50,
			lambda: 0.001,
			learning_rate: 0.15,
			stay_probability: 0.85
		};
		if (!fs.existsSync(this.config_file)) return defaults;
		let parser = (typeof JSON5 !== "undefined") ? JSON5 : require("json5");
		this._config = { ...defaults, ...parser.parse(fs.readFileSync(this.config_file, "utf8")) };
		return this._config;
	}

	static _safeNumber (arg0_value, arg1_fallback) {
		let value = Number(arg0_value);
		return Number.isFinite(value) ? value : (arg1_fallback || 0);
	}

	static _hmdBaseCode (arg0_code) {
		let code = String(arg0_code || "").split(".")[0];
		let aliases = {
			DEUTE: "DEU", DEUTW: "DEU", DEUTNP: "DEU", FRATNP: "FRA",
			GBRTENW: "GBR", GBR_SCO: "GBR", GBR_NIR: "GBR", NZL_NP: "NZL",
			RUS: "RUS", USA: "USA", KOR: "KOR", TWN: "TWN"
		};
		return aliases[code] || code;
	}

	static _getPopulationTotal (arg0_target) {
		let cohorts = this.getCohorts();
		return cohorts.reduce((sum, cohort) => sum + Math.max(0, this._safeNumber(arg0_target?.[cohort], 0)), 0);
	}

	static _getFemaleExposure (arg0_target) {
		let target = arg0_target || {};
		let return_obj = {};
		for (let age = 15; age <= 45; age += 5)
			return_obj[age] = Math.max(0, this._safeNumber(target[`f_${String(age).padStart(2, "0")}`], 0));
		return return_obj;
	}

	static _getBirthSchedule (arg0_births) {
		let births = arg0_births || {};
		let return_obj = {};
		for (let age = 15; age <= 45; age += 5)
			return_obj[age] = Math.max(0, this._safeNumber(births[`f_${String(age).padStart(2, "0")}`], 0));
		return return_obj;
	}

	static _getSurvivorship (arg0_target, arg1_deaths) {
		let target = arg0_target || {};
		let deaths = arg1_deaths || {};
		let return_obj = {};
		let survival = 1;
		for (let age = 0; age <= 80; age += 5) {
			let key = age === 0 ? "00" : String(age).padStart(2, "0");
			let population = Math.max(0, this._safeNumber(target[`f_${key}`], 0));
			let local_deaths = Math.max(0, this._safeNumber(deaths[`f_${key}`], 0));
			return_obj[age] = survival;
			let hazard = population > 0 ? Math.min(0.99, local_deaths/population) : 0;
			survival *= 1 - hazard;
		}
		return return_obj;
	}

	static _loadHMDLifeTableSurvivorship (arg0_years) {
		let years = new Set((arg0_years || []).map(String));
		let file_path = (typeof births_deaths_HMD !== "undefined") ? births_deaths_HMD.input_HMD_female_deaths_file : "";
		let return_obj = {};
		if (!file_path || !fs.existsSync(file_path)) return return_obj;
		let lines = fs.readFileSync(file_path, "utf8").split(/\r?\n/);
		for (let i = 0; i < lines.length; i++) {
			let columns = lines[i].trim().split(/\s+/);
			if (columns.length < 7 || !years.has(columns[1])) continue;
			let age = Number(columns[2]);
			let lx = Number(columns[6]);
			if (!Number.isFinite(age) || !Number.isFinite(lx) || age > 80) continue;
			if (!return_obj[columns[0]]) return_obj[columns[0]] = {};
			if (!return_obj[columns[0]][columns[1]]) return_obj[columns[0]][columns[1]] = {};
			return_obj[columns[0]][columns[1]][age] = Math.max(0, Math.min(1, lx/100000));
		}
		return return_obj;
	}

	static _deriveMetrics (arg0_target, arg1_births, arg2_deaths, arg3_donor_births, arg4_survivorship) {
		let target = arg0_target || {};
		let births = arg1_births || {};
		let deaths = arg2_deaths || {};
		let population = this._getPopulationTotal(target);
		let total_births = this._safeNumber(births.total, 0);
		let female_exposure = this._getFemaleExposure(target);
		let birth_schedule = this._getBirthSchedule(births);
		let schedule_total = Object.values(birth_schedule).reduce((sum, value) => sum + value, 0);
		let reconstruction;
		if (schedule_total > 0) {
			let fertility_rates = {};
			Object.keys(birth_schedule).forEach((age) => {
				fertility_rates[age] = female_exposure[age] > 0 ? birth_schedule[age]/female_exposure[age] : 0;
			});
			reconstruction = { fertility_rates: fertility_rates };
		} else {
			reconstruction = age_sex_classifier_demography.reconstructFertilitySchedule(
				total_births, arg3_donor_births || {}, female_exposure
			);
		}
		let fertility_rates = reconstruction.fertility_rates || {};
		let survivorship = arg4_survivorship || this._getSurvivorship(target, deaths);
		let tfr = Object.values(fertility_rates).reduce((sum, value) => sum + this._safeNumber(value, 0)*5, 0);
		let female_deaths = this._safeNumber(deaths.f_total, 0);
		let male_deaths = this._safeNumber(deaths.m_total, 0);
		let total_deaths = female_deaths + male_deaths;
		let natural_growth = population > 0 ? (total_births - total_deaths)/population : 0;
		return {
			tfr: tfr,
			mortality_rate: population > 0 ? total_deaths/population : 0,
			natural_growth: natural_growth,
			euler_lotka_r: age_sex_classifier_demography.solveEulerLotka(fertility_rates, survivorship),
			fertility_schedule_provenance: schedule_total > 0 ? "observed" : "UNWPP donor reconstruction"
		};
	}

	static _buildHMDColourLookup (arg0_year, arg1_raw_data) {
		let year = Number(arg0_year);
		let raw_data = arg1_raw_data || {};
		let lookup = {};
		let geocodes = (typeof admin_modern !== "undefined" && typeof admin_modern.getHMDColourcodesObject === "function") ?
			admin_modern.getHMDColourcodesObject() : {};
		Object.iterate(geocodes, (geocode, data) => {
			if (data.domain && (year < data.domain[0] || year > data.domain[1])) return;
			let base = geocode.split(".")[0];
			let resolved = raw_data[geocode] ? geocode : (raw_data[base] ? base : null);
			if (!resolved) return;
			for (let i = 0; i < data.colours.length; i++) lookup[data.colours[i]] = resolved;
		});
		return lookup;
	}

	static _buildHMDColourLookupPacked (arg0_year, arg1_raw_data) {
		let year = Number(arg0_year);
		let raw_data = arg1_raw_data || {};
		let lookup = {};
		let geocodes = (typeof admin_modern !== "undefined" && typeof admin_modern.getHMDColourcodesObject === "function") ?
			admin_modern.getHMDColourcodesObject() : {};
		Object.iterate(geocodes, (geocode, data) => {
			if (data.domain && (year < data.domain[0] || year > data.domain[1])) return;
			let base = geocode.split(".")[0];
			let resolved = raw_data[geocode] ? geocode : (raw_data[base] ? base : null);
			if (!resolved) return;
			for (let i = 0; i < data.colours.length; i++) {
				let parts = data.colours[i].split(",");
				if (parts.length >= 3) {
					let packed = (Number(parts[0]) << 16) | (Number(parts[1]) << 8) | Number(parts[2]);
					lookup[packed] = resolved;
				}
			}
		});
		return lookup;
	}

	static _buildISOColourLookup (arg0_raw_data) {
		let raw_data = arg0_raw_data || {};
		let source = (typeof admin_modern !== "undefined" && typeof admin_modern.getISO3ColourcodesObject === "function") ?
			admin_modern.getISO3ColourcodesObject() : {};
		let lookup = {};
		Object.iterate(source, (colour, geocodes) => {
			for (let i = 0; i < geocodes.length; i++) {
				if (raw_data[geocodes[i]]) {
					lookup[colour] = geocodes[i];
					break;
				}
			}
		});
		return lookup;
	}

	static _buildISOColourLookupPacked (arg0_raw_data) {
		let raw_data = arg0_raw_data || {};
		let source = (typeof admin_modern !== "undefined" && typeof admin_modern.getISO3ColourcodesObject === "function") ?
			admin_modern.getISO3ColourcodesObject() : {};
		let lookup = {};
		Object.iterate(source, (colour, geocodes) => {
			for (let i = 0; i < geocodes.length; i++) {
				if (raw_data[geocodes[i]]) {
					let parts = colour.split(",");
					if (parts.length >= 3) {
						let packed = (Number(parts[0]) << 16) | (Number(parts[1]) << 8) | Number(parts[2]);
						lookup[packed] = geocodes[i];
					}
					break;
				}
			}
		});
		return lookup;
	}

	static _aggregateArealCovariates (arg0_year, arg1_source, arg2_raw_data, arg3_keys) {
		let year = Number(arg0_year);
		let source = arg1_source;
		let raw_data = arg2_raw_data || {};
		let keys = arg3_keys || [];
		let geocode_path = source === "HMD" ?
			(typeof admin_modern !== "undefined" ? admin_modern.input_hmd_raster : null) :
			(typeof admin_modern !== "undefined" ? admin_modern.input_geocodes_raster : null);
		if (!geocode_path || !fs.existsSync(geocode_path)) return {};
		let geocode_raster = GeoPNG.loadImage(geocode_path);
		let colour_lookup = source === "HMD" ?
			this._buildHMDColourLookupPacked(year, raw_data) : this._buildISOColourLookupPacked(raw_data);
		let format_year = year > 2023 ? 2023 : year;
		let pop_info = this.covariates_obj.popc_?.(format_year);
		if (!pop_info || !fs.existsSync(pop_info[0])) return {};
		let population_raster = GeoPNG.loadNumberRasterImage(pop_info[0], { format: pop_info[1] || "float32" });
		let covariate_rasters = {};
		for (let k = 0; k < keys.length; k++) {
			let info = this.covariates_obj[keys[k]]?.(format_year);
			if (info && fs.existsSync(info[0]))
				covariate_rasters[keys[k]] = GeoPNG.loadNumberRasterImage(info[0], { format: info[1] || "float32" });
		}
		let aggregates = {};
		let pixels = geocode_raster.data.length/4;
		let geocode_data = geocode_raster.data;
		let pop_data = population_raster.data;
		for (let i = 0; i < pixels; i++) {
			let population = this._safeNumber(pop_data[i], 0);
			if (population <= 0) continue;
			let byte_idx = i*4;
			let packed = (geocode_data[byte_idx] << 16) | (geocode_data[byte_idx + 1] << 8) | geocode_data[byte_idx + 2];
			let geocode = colour_lookup[packed];
			if (!geocode) continue;
			if (!aggregates[geocode]) {
				aggregates[geocode] = { population: 0, sums: {} };
				for (let k = 0; k < keys.length; k++) aggregates[geocode].sums[keys[k]] = 0;
			}
			aggregates[geocode].population += population;
			for (let k = 0; k < keys.length; k++) {
				let raster = covariate_rasters[keys[k]];
				let value = raster ? Number(raster.data[i]) : NaN;
				if (Number.isFinite(value)) aggregates[geocode].sums[keys[k]] += value*population;
			}
		}
		Object.iterate(aggregates, (geocode, aggregate) => {
			aggregate.features = {};
			for (let k = 0; k < keys.length; k++)
				aggregate.features[keys[k]] = aggregate.population > 0 ? aggregate.sums[keys[k]]/aggregate.population : 0;
			delete aggregate.sums;
			let local_urban = aggregate.features.urbc_ || 0;
			let local_rural = aggregate.features.rurc_ || 0;
			let local_total = local_urban + local_rural || aggregate.features.popc_ || aggregate.population;
			aggregate.features.urban_share = local_total > 0 ? local_urban/local_total : 0;
			aggregate.features.log_population_density = Math.log(Math.max(0.01, aggregate.features.popd_ || 0));
			aggregate.features.log_gdp_ppp_pc = Math.log(Math.max(1, aggregate.features.gdp_ppp_pc || 0));
			aggregate.features.year_scaled = year/1000;
		});
		return aggregates;
	}

	static async _aggregateArealCovariatesAsync (arg0_year, arg1_source, arg2_raw_data, arg3_keys) {
		let year = Number(arg0_year);
		let source = arg1_source;
		let raw_data = arg2_raw_data || {};
		let keys = arg3_keys || [];
		let geocode_path = source === "HMD" ?
			(typeof admin_modern !== "undefined" ? admin_modern.input_hmd_raster : null) :
			(typeof admin_modern !== "undefined" ? admin_modern.input_geocodes_raster : null);
		if (!geocode_path || !fs.existsSync(geocode_path)) return {};
		let geocode_raster = GeoPNG.loadImage(geocode_path);
		let colour_lookup = source === "HMD" ?
			this._buildHMDColourLookupPacked(year, raw_data) : this._buildISOColourLookupPacked(raw_data);
		let format_year = year > 2023 ? 2023 : year;
		let pop_info = this.covariates_obj.popc_?.(format_year);
		if (!pop_info || !fs.existsSync(pop_info[0])) return {};
		let population_raster = await GeoPNG.loadNumberRasterImageAsync(pop_info[0], { format: pop_info[1] || "float32" });
		let covariate_rasters = {};
		for (let k = 0; k < keys.length; k++) {
			let info = this.covariates_obj[keys[k]]?.(format_year);
			if (info && fs.existsSync(info[0]))
				covariate_rasters[keys[k]] = await GeoPNG.loadNumberRasterImageAsync(info[0], { format: info[1] || "float32" });
		}
		let aggregates = {};
		let width = population_raster.width || 4320;
		let height = population_raster.height || 2160;
		let geocode_data = geocode_raster.data;
		let pop_data = population_raster.data;

		for (let y = 0; y < height; y++) {
			let row_offset = y*width;
			for (let x = 0; x < width; x++) {
				let i = row_offset + x;
				let population = pop_data[i];
				if (population <= 0 || isNaN(population)) continue;
				let byte_idx = i*4;
				let packed = (geocode_data[byte_idx] << 16) | (geocode_data[byte_idx + 1] << 8) | geocode_data[byte_idx + 2];
				let geocode = colour_lookup[packed];
				if (!geocode) continue;
				let agg = aggregates[geocode];
				if (!agg) {
					agg = { population: 0, sums: {} };
					for (let k = 0; k < keys.length; k++) agg.sums[keys[k]] = 0;
					aggregates[geocode] = agg;
				}
				agg.population += population;
				for (let k = 0; k < keys.length; k++) {
					let raster = covariate_rasters[keys[k]];
					if (raster) {
						let value = raster.data[i];
						if (Number.isFinite(value)) agg.sums[keys[k]] += value*population;
					}
				}
			}
			if (y % 100 === 0 && typeof Blacktraffic !== "undefined" && Blacktraffic.yield)
				await Blacktraffic.yield(0);
		}

		Object.iterate(aggregates, (geocode, aggregate) => {
			aggregate.features = {};
			for (let k = 0; k < keys.length; k++)
				aggregate.features[keys[k]] = aggregate.population > 0 ? aggregate.sums[keys[k]]/aggregate.population : 0;
			delete aggregate.sums;
			let local_urban = aggregate.features.urbc_ || 0;
			let local_rural = aggregate.features.rurc_ || 0;
			let local_total = local_urban + local_rural || aggregate.features.popc_ || aggregate.population;
			aggregate.features.urban_share = local_total > 0 ? local_urban/local_total : 0;
			aggregate.features.log_population_density = Math.log(Math.max(0.01, aggregate.features.popd_ || 0));
			aggregate.features.log_gdp_ppp_pc = Math.log(Math.max(1, aggregate.features.gdp_ppp_pc || 0));
			aggregate.features.year_scaled = year/1000;
		});
		return aggregates;
	}

	static async _collectEmpiricalRows (arg0_options) {
		let options = arg0_options || {};
		let config = this.getConfig();
		let years = options.training_years || options.years || config.training_years;
		let keys = options.covariates || config.covariates;
		let cohorts = this.getCohorts();
		let hmd_targets = (typeof age_sex_HMD !== "undefined" && typeof age_sex_HMD.A_getHMDObject === "function") ?
			age_sex_HMD.A_getHMDObject() : {};
		let unwpp_targets = (typeof age_sex_UNWPP !== "undefined" && typeof age_sex_UNWPP.A_getUNWPPGroups === "function") ?
			await age_sex_UNWPP.A_getUNWPPGroups() : {};
		let hmd_components = (typeof births_deaths_HMD !== "undefined" && typeof births_deaths_HMD.A_getHMDGroups === "function") ?
			births_deaths_HMD.A_getHMDGroups() : { births: {}, female_deaths: {}, male_deaths: {} };
		let unwpp_components = (typeof births_deaths_UNWPP !== "undefined" && typeof births_deaths_UNWPP.A_getUNWPPGroups === "function") ?
			await births_deaths_UNWPP.A_getUNWPPGroups() : { births: {}, deaths: {} };
		let hmd_survivorship = this._loadHMDLifeTableSurvivorship(years.filter((year) => Number(year) < 1950));
		let global_donor = {};
		let donor_count = 0;
		if (unwpp_components && unwpp_components.births) {
			Object.iterate(unwpp_components.births, (iso3, year_obj) => {
				let donor = this._getBirthSchedule(year_obj["1950"]);
				if (Object.values(donor).some((value) => value > 0)) {
					Object.iterate(donor, (age, value) => global_donor[age] = (global_donor[age] || 0) + value);
					donor_count++;
				}
			});
		}
		if (donor_count > 0) Object.keys(global_donor).forEach((age) => global_donor[age] /= donor_count);

		//Concurrently aggregate areal covariates across worker threads
		let year_aggregates_list = await GeoPNG.processTimeseriesParallel({
			concurrency: options.concurrency || 4,
			items: years,
			name: "Step A: Empirical Covariates",
			task_generator: (year_val) => {
				let year = Number(year_val);
				let source = year < 1950 ? "HMD" : "UNWPP";
				let target_data = source === "HMD" ? hmd_targets : unwpp_targets;
				let geocode_path = source === "HMD" ?
					(typeof admin_modern !== "undefined" ? admin_modern.input_hmd_raster : null) :
					(typeof admin_modern !== "undefined" ? admin_modern.input_geocodes_raster : null);
				let colour_lookup_packed = source === "HMD" ?
					this._buildHMDColourLookupPacked(year, target_data) :
					this._buildISOColourLookupPacked(target_data);
				let format_year = year > 2023 ? 2023 : year;
				let pop_info = this.covariates_obj.popc_?.(format_year);
				let covariate_paths = {};
				for (let k = 0; k < keys.length; k++) {
					let info = this.covariates_obj[keys[k]]?.(format_year);
					if (info && fs.existsSync(info[0]))
						covariate_paths[keys[k]] = { path: info[0], format: info[1] || "float32" };
				}

				return {
					colour_lookup_packed: colour_lookup_packed,
					covariate_paths: covariate_paths,
					geocode_path: geocode_path,
					keys: keys,
					population_format: pop_info ? (pop_info[1] || "float32") : "float32",
					population_path: pop_info ? pop_info[0] : null,
					type: "aggregate_areal_covariates",
					year: year
				};
			},
			use_workers: options.use_workers !== undefined ? options.use_workers : true,
			handler: async (year_val) => {
				let year = Number(year_val);
				let source = year < 1950 ? "HMD" : "UNWPP";
				let target_data = source === "HMD" ? hmd_targets : unwpp_targets;
				return await this._aggregateArealCovariatesAsync(year, source, target_data, keys);
			}
		});

		let rows = [];

		for (let y = 0; y < years.length; y++) {
			let year = Number(years[y]);
			let source = year < 1950 ? "HMD" : "UNWPP";
			let target_data = source === "HMD" ? hmd_targets : unwpp_targets;
			let aggregates = year_aggregates_list[y] || {};
			Object.iterate(aggregates, (geocode, aggregate) => {
				let target = target_data[geocode]?.[String(year)];
				if (!target) return;
				let iso3 = source === "HMD" ? this._hmdBaseCode(geocode) : geocode;
				let births;
				let deaths;
				let donor;
				if (source === "HMD") {
					births = { total: hmd_components.births[geocode]?.[String(year)] || hmd_components.births[geocode.split(".")[0]]?.[String(year)] || 0 };
					deaths = {
						f_total: hmd_components.female_deaths[geocode]?.[String(year)] || hmd_components.female_deaths[geocode.split(".")[0]]?.[String(year)] || 0,
						m_total: hmd_components.male_deaths[geocode]?.[String(year)] || hmd_components.male_deaths[geocode.split(".")[0]]?.[String(year)] || 0
					};
					donor = this._getBirthSchedule(unwpp_components.births[iso3]?.["1950"]) || global_donor;
					if (!Object.values(donor).some((value) => value > 0)) donor = global_donor;
				} else {
					births = unwpp_components.births[geocode]?.[String(year)] || {};
					deaths = unwpp_components.deaths[geocode]?.[String(year)] || {};
					donor = this._getBirthSchedule(births);
				}
				let population = this._getPopulationTotal(target);
				if (population <= 0) return;
				let total = cohorts.reduce((sum, cohort) => sum + this._safeNumber(target[cohort], 0), 0);
				rows.push({
					features: aggregate.features,
					geocode: iso3,
					metrics: this._deriveMetrics(
						target,
						births,
						deaths,
						donor,
						source === "HMD" ?
							(hmd_survivorship[geocode]?.[String(year)] || hmd_survivorship[geocode.split(".")[0]]?.[String(year)]) :
							null
					),
					population: population,
					source: source,
					target: cohorts.map((cohort) => total > 0 ? this._safeNumber(target[cohort], 0)/total : 0),
					year: year
				});
			});
		}
		return rows;
	}

	static _addDeltasAndSeeds (arg0_rows) {
		let rows = arg0_rows || [];
		let groups = {};
		for (let i = 0; i < rows.length; i++) {
			if (!groups[rows[i].geocode]) groups[rows[i].geocode] = [];
			groups[rows[i].geocode].push(rows[i]);
		}
		Object.iterate(groups, (geocode, local_rows) => {
			local_rows.sort((a, b) => a.year - b.year);
			for (let i = 0; i < local_rows.length; i++) {
				let previous = local_rows[i - 1];
				let interval = previous ? Math.max(1, local_rows[i].year - previous.year) : 1;
				local_rows[i].metrics.delta_tfr = previous ? (local_rows[i].metrics.tfr - previous.metrics.tfr)/interval : 0;
				local_rows[i].metrics.delta_mortality = previous ? (local_rows[i].metrics.mortality_rate - previous.metrics.mortality_rate)/interval : 0;
				local_rows[i].stage = age_sex_classifier_demography.seedStage(local_rows[i].metrics, this.getConfig().stage_thresholds);
			}
		});
		return rows;
	}

	static async A_buildTrainingDataset (arg0_options) {
		let options = arg0_options || {};
		let rows = options.observations || await this._collectEmpiricalRows(options);
		rows = this._addDeltasAndSeeds(rows);
		fs.mkdirSync(path.dirname(this.training_dataset_file), { recursive: true });
		fs.writeFileSync(this.training_dataset_file, JSON.stringify({ cohorts: this.getCohorts(), rows: rows }, null, 2));
		return rows;
	}

	static async B_trainStageClassifier (arg0_options) {
		let options = arg0_options || {};
		let rows = options.observations || JSON.parse(fs.readFileSync(this.training_dataset_file, "utf8")).rows;
		let config = this.getConfig();
		let feature_keys = age_sex_classifier_demography.selectCovariates(rows, {
			candidate_keys: options.covariates || config.covariates.concat([
				"urban_share", "log_population_density", "log_gdp_ppp_pc", "year_scaled"
			])
		});
		let seed_model = age_sex_classifier_demography.fitBayesClassifier(rows, feature_keys);
		let grouped = {};
		for (let i = 0; i < rows.length; i++) {
			if (!grouped[rows[i].geocode]) grouped[rows[i].geocode] = [];
			grouped[rows[i].geocode].push(rows[i]);
		}
		let constrained_rows = [];
		Object.iterate(grouped, (geocode, local_rows) => {
			constrained_rows.push(...age_sex_classifier_demography.constrainStageSequence(local_rows, seed_model, {
				initial_from_emission: true,
				stay_probability: config.stay_probability
			}));
		});
		let final_model = age_sex_classifier_demography.fitBayesClassifier(constrained_rows, feature_keys);
		final_model.transition = { allowed: ["same", "next"], stay_probability: config.stay_probability };
		final_model.training = { sample_count: constrained_rows.length, sources: ["HMD", "UNWPP"] };
		fs.mkdirSync(this.archetype_folder, { recursive: true });
		fs.writeFileSync(this.stage_model_file, JSON.stringify(final_model, null, 2));
		fs.writeFileSync(this.training_dataset_file, JSON.stringify({ cohorts: this.getCohorts(), rows: constrained_rows }, null, 2));
		return { model: final_model, rows: constrained_rows };
	}

	static async C_trainArchetypeModels (arg0_options) {
		let options = arg0_options || {};
		let config = this.getConfig();
		let dataset = options.observations ? { rows: options.observations } :
			JSON.parse(fs.readFileSync(this.training_dataset_file, "utf8"));
		let stage_model = options.stage_model || JSON.parse(fs.readFileSync(this.stage_model_file, "utf8"));
		let cohorts = this.getCohorts();
		let model_entries = [];
		fs.mkdirSync(this.archetype_folder, { recursive: true });

		for (let s = 0; s < age_sex_classifier_demography.stages.length; s++) {
			let stage = age_sex_classifier_demography.stages[s];
			let rows = dataset.rows.filter((row) => row.stage === stage);
			if (rows.length < 2) continue;
			let model_path = `${this.archetype_folder}${stage}_multinomial.json`;
			let model = await Statistics.trainMultinomialLogitModel(model_path, {
				keys: stage_model.feature_keys,
				weights: rows.map((row) => row.population),
				X: rows.map((row) => stage_model.feature_keys.map((key) => this._safeNumber(row.features?.[key], 0))),
				Y: rows.map((row) => row.target)
			}, {
				classes: cohorts,
				debug: options.debug === true,
				fit_intercept: true,
				lambda: this._safeNumber(options.lambda, config.lambda),
				learning_rate: this._safeNumber(options.learning_rate, config.learning_rate),
				max_iterations: Math.min(50, this._safeNumber(options.max_iterations, config.max_iterations)),
				proportions: true,
				reference_class: cohorts[0]
			});
			if (model) {
				model.archetype = stage;
				model.training.sources = Array.from(new Set(rows.map((row) => row.source)));
				model.training.year_domain = [Math.min(...rows.map((row) => row.year)), Math.max(...rows.map((row) => row.year))];
				fs.writeFileSync(model_path, JSON.stringify(model, null, 2));
				model_entries.push({ stage: stage, path: model_path, sample_count: rows.length });
			}
		}
		let manifest = {
			type: "cdt_archetype_mixture",
			classes: cohorts,
			covariates: stage_model.feature_keys,
			max_iterations: 50,
			models: model_entries,
			stage_model: this.stage_model_file
		};
		fs.writeFileSync(this.manifest_file, JSON.stringify(manifest, null, 2));
		return manifest;
	}

	static D_buildM1Weights (arg0_options) {
		let options = arg0_options || {};
		let dataset = options.observations ? { rows: options.observations } :
			JSON.parse(fs.readFileSync(this.training_dataset_file, "utf8"));
		let stage_model = options.stage_model || JSON.parse(fs.readFileSync(this.stage_model_file, "utf8"));
		let grouped = {};
		for (let i = 0; i < dataset.rows.length; i++) {
			let row = dataset.rows[i];
			if (!grouped[row.geocode]) grouped[row.geocode] = [];
			grouped[row.geocode].push(row);
		}
		let output = {};
		Object.iterate(grouped, (geocode, rows) => {
			let sequence = age_sex_classifier_demography.constrainStageSequence(rows, stage_model, {
				initial_from_emission: true,
				stay_probability: stage_model.transition?.stay_probability || 0.85
			});
			output[geocode] = {};
			for (let i = 0; i < sequence.length; i++)
				output[geocode][sequence[i].year] = sequence[i].stage_weights;
		});
		fs.mkdirSync(path.dirname(this.weights_file), { recursive: true });
		fs.writeFileSync(this.weights_file, JSON.stringify(output, null, 2));
		return output;
	}

	static _resolveWeights (arg0_all_weights, arg1_geocode, arg2_year) {
		let local = arg0_all_weights?.[arg1_geocode];
		let stages = age_sex_classifier_demography.stages;
		if (!local) return Object.fromEntries(stages.map((stage, index) => [stage, index === 0 ? 1 : 0]));
		let years = Object.keys(local).map(Number).filter((year) => year <= Number(arg2_year)).sort((a, b) => b - a);
		if (years.length === 0) return Object.fromEntries(stages.map((stage, index) => [stage, index === 0 ? 1 : 0]));
		return local[years[0]];
	}

	static predictM1 (arg0_features, arg1_stage_weights, arg2_models) {
		let features = arg0_features || {};
		let stage_weights = arg1_stage_weights || {};
		let models = arg2_models || {};
		let cohorts = this.getCohorts();
		let probabilities = Object.fromEntries(cohorts.map((cohort) => [cohort, 0]));
		let total_weight = 0;
		Object.iterate(models, (stage, model) => {
			let weight = Math.max(0, this._safeNumber(stage_weights[stage], 0));
			if (weight <= 0) return;
			let local = Statistics.predictMultinomialProbabilities(features, model);
			for (let c = 0; c < cohorts.length; c++)
				probabilities[cohorts[c]] += weight*this._safeNumber(local[cohorts[c]], 0);
			total_weight += weight;
		});
		let total = Object.values(probabilities).reduce((sum, value) => sum + value, 0);
		if (total_weight <= 0 || total <= 0)
			return Object.fromEntries(cohorts.map((cohort) => [cohort, 1/cohorts.length]));
		Object.keys(probabilities).forEach((cohort) => probabilities[cohort] /= total);
		return probabilities;
	}

	static loadM2Catalogues () {
		return {
			fertility: age_sex_classifier_shocks.loadCatalogue(this.fertility_shocks_file),
			migration: age_sex_classifier_shocks.loadCatalogue(this.migration_shocks_file),
			mortality: age_sex_classifier_shocks.loadCatalogue(this.mortality_shocks_file)
		};
	}

	static applyM2 (arg0_counts, arg1_context) {
		return age_sex_classifier_shocks.applyShocks(arg0_counts, {
			...arg1_context,
			catalogues: arg1_context?.catalogues || this.loadM2Catalogues(),
			cohorts: this.getCohorts()
		});
	}

	/**
	 * Generates geocode-bounded M1 mixture rasters without isotonic/PAVA coupling.
	 */
	static async E_generateM1Rasters (arg0_options) {
		return await age_sex_classifier_rasters.generateM1(this, arg0_options || {});
	}

	/**
	 * Applies M2 priors, gives direct HMD/UNWPP observations precedence, and clamps
	 * the resulting simplex to Stadestér population without PAVA.
	 */
	static async F_applyM2AndComposite (arg0_options) {
		return await age_sex_classifier_rasters.applyM2(this, arg0_options || {});
	}

	/**
	 * Runs the standalone classifier across all HYDE years (10000 BC to 2025 AD).
	 * @alias age_sex_classifier.processRasters
	 *
	 * @param {Object} [arg0_options]
	 *  @param {number} [arg0_options.concurrency=4]
	 *  @param {Array<string>} [arg0_options.exclude] - Steps to exclude: ["A", "B", "C", "D", "E", "F"].
	 *  @param {boolean} [arg0_options.publish=false] - If true, copies final composite rasters into age_sex.output_rasters.
	 *  @param {Array<number>} [arg0_options.raster_years] - Custom subset of raster years to process (defaults to all 128 HYDE years).
	 *  @param {Array<number>} [arg0_options.training_years] - Custom empirical anchor years (defaults to config.training_years).
	 *  @param {Array<number>} [arg0_options.years] - Alias for raster_years.
	 *
	 * @returns {Promise<Object>}
	 */
	static async processRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};

		//Initialise options
		if (!options.exclude) options.exclude = [];
		let config = this.getConfig();
		let raster_years = options.raster_years || options.years || this.getHYDEYears();
		let training_years = options.training_years || config.training_years;

		//Declare local instance variables
		let pipeline_start = Date.now();
		let rows;

		let formatDuration = (start_time) => {
			let elapsed = (Date.now() - start_time)/1000;
			return `${elapsed.toFixed(2)}s`;
		};

		let sendTelemetry = (step_name, percent) => {
			if (typeof require !== "undefined") {
				try {
					let ipc = require("electron").ipcRenderer;
					if (ipc) {
						ipc.send("training:telemetry", {
							task_name: `Classifier [${step_name}]`,
							percent: percent,
							progress: percent/100
						});
					}
				} catch (e) {}
			}
		};

		console.log(`========================================================================`);
		console.log(`[age_sex_classifier] Starting Standalone Counterfactual Pipeline`);
		console.log(`- Raster temporal domain: ${raster_years.length} HYDE years (${raster_years[0]} to ${raster_years[raster_years.length - 1]})`);
		console.log(`- Empirical calibration:  ${training_years.length} benchmark years (${training_years[0]} to ${training_years[training_years.length - 1]})`);
		console.log(`- Destination folder:     ${this.output_rasters}`);
		if (options.publish)
			console.log(`- Production target:      ${typeof age_sex !== "undefined" ? age_sex.output_rasters : "N/A"}`);
		console.log(`========================================================================`);

		//Step A: Empirical training dataset
		if (!options.exclude.includes("A")) {
			let step_start = Date.now();
			console.log(`- [age_sex_classifier] Step A: Building empirical training dataset (${training_years.length} anchor years)...`);
			sendTelemetry("Step A: Dataset", 5);
			if (typeof Blacktraffic !== "undefined" && Blacktraffic.yield) await Blacktraffic.yield(0);
			rows = await this.A_buildTrainingDataset({ ...options, training_years: training_years });
			console.log(`- [age_sex_classifier] Step A completed in ${formatDuration(step_start)} (${rows.length} empirical rows).`);
		}

		//Step B: Bayesian stage classifier
		if (!options.exclude.includes("B")) {
			let step_start = Date.now();
			console.log(`- [age_sex_classifier] Step B: Training Bayes stage transition classifier...`);
			sendTelemetry("Step B: Bayes", 20);
			if (typeof Blacktraffic !== "undefined" && Blacktraffic.yield) await Blacktraffic.yield(0);
			await this.B_trainStageClassifier({ ...options, observations: rows });
			console.log(`- [age_sex_classifier] Step B completed in ${formatDuration(step_start)}.`);
		}

		//Step C: CDT archetype multinomial logit models
		if (!options.exclude.includes("C")) {
			let step_start = Date.now();
			console.log(`- [age_sex_classifier] Step C: Fitting CDT archetype multinomial models...`);
			sendTelemetry("Step C: Archetypes", 40);
			if (typeof Blacktraffic !== "undefined" && Blacktraffic.yield) await Blacktraffic.yield(0);
			await this.C_trainArchetypeModels(options);
			console.log(`- [age_sex_classifier] Step C completed in ${formatDuration(step_start)}.`);
		}

		//Step D: Build M1 weights sequence
		if (!options.exclude.includes("D")) {
			let step_start = Date.now();
			console.log(`- [age_sex_classifier] Step D: Building M1 archetype weights sequence...`);
			sendTelemetry("Step D: Weights", 55);
			if (typeof Blacktraffic !== "undefined" && Blacktraffic.yield) await Blacktraffic.yield(0);
			this.D_buildM1Weights(options);
			console.log(`- [age_sex_classifier] Step D completed in ${formatDuration(step_start)}.`);
		}

		//Step E: Generate M1 mixture rasters
		if (!options.exclude.includes("E")) {
			let step_start = Date.now();
			console.log(`- [age_sex_classifier] Step E: Generating M1 mixture rasters for ${raster_years.length} years...`);
			sendTelemetry("Step E: M1 Rasters", 60);
			if (typeof Blacktraffic !== "undefined" && Blacktraffic.yield) await Blacktraffic.yield(0);
			await this.E_generateM1Rasters({ ...options, years: raster_years });
			console.log(`- [age_sex_classifier] Step E completed in ${formatDuration(step_start)}.`);
		}

		//Step F: Apply M2 shocks and composite with empirical masks
		if (!options.exclude.includes("F")) {
			let step_start = Date.now();
			console.log(`- [age_sex_classifier] Step F: Applying M2 priors and compositing cohorts for ${raster_years.length} years...`);
			sendTelemetry("Step F: M2 Compositing", 85);
			if (typeof Blacktraffic !== "undefined" && Blacktraffic.yield) await Blacktraffic.yield(0);
			await this.F_applyM2AndComposite({ ...options, years: raster_years });
			console.log(`- [age_sex_classifier] Step F completed in ${formatDuration(step_start)}.`);
		}

		sendTelemetry("Complete", 100);
		console.log(`========================================================================`);
		console.log(`[age_sex_classifier] Pipeline completed in ${formatDuration(pipeline_start)}.`);
		console.log(`[age_sex_classifier] Output directories:`);
		console.log(`  - M1 probabilities:  ${this.m1_rasters}`);
		console.log(`  - M2 clamped:        ${this.m2_rasters}`);
		console.log(`  - Composite cohorts: ${this.output_rasters}`);
		if (options.publish && typeof age_sex !== "undefined")
			console.log(`  - Production target: ${age_sex.output_rasters}`);
		console.log(`========================================================================`);

		//Return statement
		return {
			manifest: this.manifest_file,
			weights: this.weights_file,
			m1_rasters: this.m1_rasters,
			m2_rasters: this.m2_rasters,
			output_rasters: this.output_rasters,
			production_rasters: (typeof age_sex !== "undefined") ? age_sex.output_rasters : null,
			years_processed: raster_years,
			total_years: raster_years.length,
			m2: [this.fertility_shocks_file, this.migration_shocks_file, this.mortality_shocks_file],
			pava: false
		};
	}
};
