global.births_deaths_HMD = class {
	static bf = `${h2}/births_deaths_HMD/`;
	static input_HMD_births_file = `${h1}/age_sex_HMD/births/Births.txt`;
	static input_HMD_female_deaths_file = `${h1}/age_sex_HMD/lt_female/fltper_1x1.txt`;
	static input_HMD_male_deaths_file = `${h1}/age_sex_HMD/lt_male/mltper_1x1.txt`;
	static intermediate_backcalculated_births_folder = `${this.bf}/0.backcalculated_births/`;
	static intermediate_backcalculated_female_deaths_folder = `${this.bf}/0.backcalculated_female_deaths/`;
	static intermediate_backcalculated_male_deaths_folder = `${this.bf}/0.backcalculated_male_deaths/`;
	static output_crude_births_folder = `${this.bf}/1.crude_births/`;
	static output_female_crude_deaths_folder = `${this.bf}/1.female_crude_deaths/`;
	static output_male_crude_deaths_folder = `${this.bf}/1.male_crude_deaths/`;
	
	/**
	 * Helper function to cubic-spline interpolate all HMD national series onto HYDE years,
	 * mirroring the temporal alignment in age_sex_HMD.
	 *
	 * @returns {Object} An object containing interpolated births/female_deaths/male_deaths keyed by PopName -> HYDE year.
	 */
	static _getInterpolatedSeries () {
		//Declare local instance variables
		let groups = this.hmd_groups || this.A_getHMDGroups();
		let hyde_years = landuse_HYDE.sorted_hyde_years;
		let return_obj = {};
		
		//Interpolate each series independently onto the HYDE temporal domain
		Object.iterate(groups, (series_key, series_obj) => {
			return_obj[series_key] = {};
			
			Object.iterate(series_obj, (pop_name, year_obj) => {
				return_obj[series_key][pop_name] = Object.cubicSplineInterpolation(year_obj, { years: hyde_years });
			});
		});
		
		//Return statement
		return return_obj;
	}
	
	/**
	 * Parses HMD births, life tables, and population files into national yearly aggregates.
	 * Births are read directly from Births.txt totals. Life tables only provide central
	 * death rates (mx), so absolute deaths are derived as the sum of mx(age) multiplied
	 * by the single-age population from Population.txt, per sex.
	 *
	 * Unlike UNWPP, missing data here is legitimate (partial coverage), not a glitch.
	 *
	 * @returns {Object} An object containing births, female_deaths, and male_deaths keyed by PopName -> Year.
	 */
	static A_getHMDGroups () {
		//Declare local instance variables
		let births_obj = {};
		let population_obj = {};
		
		//1. Parse Births.txt (PopName, Year, Female, Male, Total)
		let births_text = fs.readFileSync(this.input_HMD_births_file, "utf8");
		let births_lines = births_text.split(/\r?\n/);
		
		for (let i = 0; i < births_lines.length; i++) {
			let line = births_lines[i].trim();
			
			//Skip empty lines, file headers, or table headers
			if (!line || line.startsWith("Births") || line.startsWith("PopName")) continue;
			
			let cols = line.split(/\s+/);
			if (cols.length < 5) continue;
			
			let pop_name = cols[0];
			let year = cols[1];
			let total = parseFloat(cols[4]) || 0;
			
			if (!births_obj[pop_name]) births_obj[pop_name] = {};
			births_obj[pop_name][year] = total;
		}
		
		//2. Parse Population.txt into single-age populations per sex (needed to weight mx rates)
		let population_text = fs.readFileSync(age_sex_HMD.input_HMD_population_file, "utf8");
		let population_lines = population_text.split(/\r?\n/);
		
		for (let i = 0; i < population_lines.length; i++) {
			let line = population_lines[i].trim();
			
			if (!line || line.startsWith("Population") || line.startsWith("PopName")) continue;
			
			let cols = line.split(/\s+/);
			if (cols.length < 5) continue;
			
			let pop_name = cols[0];
			let year = cols[1];
			let parsed_age = parseInt(cols[2]);
			if (isNaN(parsed_age)) continue;
			
			let female = parseFloat(cols[3]) || 0;
			let male = parseFloat(cols[4]) || 0;
			
			if (!population_obj[pop_name]) population_obj[pop_name] = {};
			if (!population_obj[pop_name][year]) population_obj[pop_name][year] = {};
			population_obj[pop_name][year][parsed_age] = { f: female, m: male };
		}
		
		//3. Parse life tables into single-age central death rates (mx)
		let parseLifeTable = function (file_path) {
			let return_obj = {};
			let raw_text = fs.readFileSync(file_path, "utf8");
			let lines = raw_text.split(/\r?\n/);
			
			for (let i = 0; i < lines.length; i++) {
				let line = lines[i].trim();
				
				//Skip empty lines, file headers, or table headers
				if (!line || line.startsWith("Life tables") || line.startsWith("PopName")) continue;
				
				let cols = line.split(/\s+/);
				if (cols.length < 4) continue;
				
				let pop_name = cols[0];
				let year = cols[1];
				let parsed_age = parseInt(cols[2]);
				if (isNaN(parsed_age)) continue;
				
				let mx = parseFloat(cols[3]) || 0;
				
				if (!return_obj[pop_name]) return_obj[pop_name] = {};
				if (!return_obj[pop_name][year]) return_obj[pop_name][year] = {};
				return_obj[pop_name][year][parsed_age] = mx;
			}
			
			return return_obj;
		};
		
		let female_mx = parseLifeTable(this.input_HMD_female_deaths_file);
		let male_mx = parseLifeTable(this.input_HMD_male_deaths_file);
		
		//4. Derive absolute deaths: deaths = sum over ages of mx(age) * population(age)
		let deriveDeaths = function (mx_obj, sex_key) {
			let return_obj = {};
			
			Object.iterate(mx_obj, (pop_name, year_obj) => {
				Object.iterate(year_obj, (year, age_obj) => {
					let local_pop_year = population_obj[pop_name]?.[year];
					if (!local_pop_year) return;
					
					let local_total = 0;
					Object.iterate(age_obj, (age, mx) => {
						let local_pop = local_pop_year[age]?.[sex_key];
						if (local_pop !== undefined) local_total += mx * local_pop;
					});
					
					if (!return_obj[pop_name]) return_obj[pop_name] = {};
					return_obj[pop_name][year] = local_total;
				});
			});
			
			return return_obj;
		};
		
		let female_deaths_obj = deriveDeaths(female_mx, "f");
		let male_deaths_obj = deriveDeaths(male_mx, "m");
		
		//Save to the class as a static variable and return
		let return_data = {
			births: births_obj,
			female_deaths: female_deaths_obj,
			male_deaths: male_deaths_obj
		};
		this.hmd_groups = return_data;
		return return_data;
	}
	
	/**
	 * Backcalculates births/deaths over the pre-1950 HYDE domain using the UNWPP 1950
	 * clamped rasters as the observed spatial base, scaled to interpolated HMD national
	 * aggregates. HMD coverage is partial by design: regions or years without data
	 * produce zero pixels natively. Years in which no region has any data at all
	 * (e.g. 10000 BC) produce no raster whatsoever.
	 *
	 * @returns {Promise<void>}
	 */
	static async B_generateHMDRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;

		//Declare local instance variables
		let hmd_series = this._getInterpolatedSeries();
		let geocode_obj = admin_modern.getHMDColourcodesObject();
		let geocode_raster = GeoPNG.loadImage(admin_modern.input_hmd_raster);
		let hyde_years = landuse_HYDE.sorted_hyde_years;
		
		//Map colours to geocodes for fast pixel lookup
		let colour_to_geocode = {};
		Object.iterate(geocode_obj, (geocode, data) => {
			if (data.colours) {
				for (let i = 0; i < data.colours.length; i++) {
					let colour = data.colours[i];
					if (!colour_to_geocode[colour]) colour_to_geocode[colour] = [];
					colour_to_geocode[colour].push(geocode);
				}
			}
		});
		
		//Define the three raster series to backcalculate:
		//[intermediate_folder, file_prefix, series_key, UNWPP 1950 base path]
		let raster_series = [
			[this.intermediate_backcalculated_births_folder, "births", "births", `${births_deaths_UNWPP.output_crude_births_folder}births_1950.png`],
			[this.intermediate_backcalculated_female_deaths_folder, "female_deaths", "female_deaths", `${births_deaths_UNWPP.output_female_crude_deaths_folder}female_deaths_1950.png`],
			[this.intermediate_backcalculated_male_deaths_folder, "male_deaths", "male_deaths", `${births_deaths_UNWPP.output_male_crude_deaths_folder}male_deaths_1950.png`]
		];
		
		//Iterate over all raster series
		for (let s = 0; s < raster_series.length; s++) {
			let intermediate_folder = raster_series[s][0];
			let file_prefix = raster_series[s][1];
			let series_key = raster_series[s][2];
			let base_1950_path = raster_series[s][3];
			
			if (!fs.existsSync(base_1950_path)) {
				console.warn(`[WARN] Missing UNWPP 1950 base raster: ${base_1950_path}. Skipping ${file_prefix} series.`);
				continue;
			}
			
			let base_sums = {};
			let base_raster = GeoPNG.loadNumberRasterImage(base_1950_path, {
				format: "float32"
			});
			
			//1. Calculate the 1950 starting mass for each HMD region
			GeoPNG.operateNumberRasterImage({
				file_path: base_1950_path,
				format: "float32",
				function: (local_index, local_value) => {
					let colour_key = [
						geocode_raster.data[local_index],
						geocode_raster.data[local_index + 1],
						geocode_raster.data[local_index + 2]
					].join(",");
					
					let geocodes = colour_to_geocode[colour_key];
					if (geocodes) {
						for (let x = 0; x < geocodes.length; x++) {
							Object.modifyValue(base_sums, geocodes[x], local_value);
						}
					}
				}
			});
			
			console.log(`- Loaded 1950 base spatial mask for ${file_prefix}`);
			
			//2. Backcalculate strictly over pre-1950 HYDE temporal boundaries
			for (let y = 0; y < hyde_years.length; y++) {
				let year = hyde_years[y];
				let year_num = parseInt(year);
				
				//GUARD CLAUSE: HMD is strictly for historical backcalculation prior to the UNWPP era.
				if (year_num >= 1950) continue;
				
				let output_path = `${intermediate_folder}${file_prefix}_${year}.png`;
				
				if (!overwrite && fs.existsSync(output_path)) continue;
				
				let scalars = {};
				let has_data = false;
				
				//Calculate domain-restricted scalars
				Object.iterate(geocode_obj, (geocode, data) => {
					let in_domain = true;
					if (data.domain) {
						if (year_num < data.domain[0] || year_num > data.domain[1]) {
							in_domain = false;
						}
					}
					
					let hmd_code = geocode.split(".")[0];
					
					if (in_domain) {
						let target_val = hmd_series[series_key][hmd_code]?.[year];
						//Spline overshoot can yield negatives; clamp to zero
						target_val = (target_val !== undefined && target_val > 0) ? target_val : 0;
						let base_pop = base_sums[geocode] || 0;
						
						if (target_val > 0 && base_pop > 0) {
							scalars[geocode] = target_val / base_pop;
							has_data = true;
						} else {
							scalars[geocode] = 0;
						}
					} else {
						scalars[geocode] = 0;
					}
				});
				
				//If no regions have data for this time period (e.g. 10000 BC), do not produce an output raster
				if (!has_data) continue;
				
				//3. Dasymetrically save the historical raster. Regions without HMD coverage
				//natively resolve to zero pixels, as partial coverage is expected.
				GeoPNG.saveNumberRasterImage({
					file_path: output_path,
					format: "float32",
					width: base_raster.width,
					height: base_raster.height,
					function: (local_index) => {
						let byte_index = local_index * 4;
						let colour_key = [
							geocode_raster.data[byte_index],
							geocode_raster.data[byte_index + 1],
							geocode_raster.data[byte_index + 2]
						].join(",");
						
						let geocodes = colour_to_geocode[colour_key];
						let local_value = base_raster.data[local_index];
						
						if (geocodes) {
							for (let x = 0; x < geocodes.length; x++) {
								let scalar = scalars[geocodes[x]];
								if (scalar !== undefined) {
									return local_value * scalar;
								}
							}
						}
						return 0;
					}
				});
				
				console.log(`Processed HMD backcalculation: ${output_path}`);
				await Blacktraffic.yield();
			}
		}
	}
	
	/**
	 * Clamps backcalculated HMD rasters to the Stadestér population footprint for each
	 * pre-1950 year. Pixels where Stadestér asserts zero population are strictly zeroed;
	 * national totals are re-anchored exactly to interpolated HMD aggregates over the
	 * populated footprint. Pixels populated in the target year but empty in the 1950 base
	 * are injected at the national crude rate proportional to local population.
	 *
	 * Regions without HMD coverage resolve to zero pixels, as partial coverage is expected.
	 * Years in which no backcalculated raster exists at all are skipped entirely.
	 *
	 * @returns {Promise<void>}
	 */
	static async C_clampToStadester (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;

		//Declare local instance variables
		let hmd_series = this._getInterpolatedSeries();
		let geocode_obj = admin_modern.getHMDColourcodesObject();
		let geocode_raster = GeoPNG.loadImage(admin_modern.input_hmd_raster);
		let hyde_years = landuse_HYDE.sorted_hyde_years;
		
		//Map colours to geocodes for fast pixel lookup
		let colour_to_geocode = {};
		Object.iterate(geocode_obj, (geocode, data) => {
			if (data.colours) {
				for (let i = 0; i < data.colours.length; i++) {
					let colour = data.colours[i];
					if (!colour_to_geocode[colour]) colour_to_geocode[colour] = [];
					colour_to_geocode[colour].push(geocode);
				}
			}
		});
		
		//Define the three raster series to clamp: [intermediate_folder, output_folder, file_prefix, series_key]
		let raster_series = [
			[this.intermediate_backcalculated_births_folder, this.output_crude_births_folder, "births", "births"],
			[this.intermediate_backcalculated_female_deaths_folder, this.output_female_crude_deaths_folder, "female_deaths", "female_deaths"],
			[this.intermediate_backcalculated_male_deaths_folder, this.output_male_crude_deaths_folder, "male_deaths", "male_deaths"]
		];
		
		//Iterate over temporal bounds
		for (let y = 0; y < hyde_years.length; y++) {
			let year = hyde_years[y];
			let year_num = parseInt(year);
			
			//GUARD CLAUSE: HMD is strictly for historical backcalculation prior to the UNWPP era.
			if (year_num >= 1950) continue;
			
			let pop_path = `${population_Stadester.input_popc_folder}stadester_population_${year}.png`;
			
			//Guard clause if no Stadestér temporal anchor exists for this year
			if (!fs.existsSync(pop_path)) continue;
			
			//Guard clause: if no backcalculated rasters exist for this year at all
			//(i.e. no HMD coverage for the period), do not produce clamped outputs
			let has_any_backcalc = false;
			for (let s = 0; s < raster_series.length; s++) {
				if (fs.existsSync(`${raster_series[s][0]}${raster_series[s][2]}_${year}.png`)) {
					has_any_backcalc = true;
					break;
				}
			}
			if (!has_any_backcalc) continue;
			
			console.log(`Processing Stadester clamping of HMD births/deaths for year: ${year}`);
			
			//1. Load Stadester popc anchor raster and compute national population sums over HMD regions
			let stadester_raster = GeoPNG.loadNumberRasterImage(pop_path, {
				format: "float32"
			});
			
			let stadester_sums = {};
			for (let i = 0; i < stadester_raster.data.length; i++) {
				let local_value = stadester_raster.data[i];
				if (local_value <= 0) continue;
				
				let byte_index = i * 4;
				let colour_key = [
					geocode_raster.data[byte_index],
					geocode_raster.data[byte_index + 1],
					geocode_raster.data[byte_index + 2]
				].join(",");
				let geocodes = colour_to_geocode[colour_key];
				
				if (geocodes)
					for (let x = 0; x < geocodes.length; x++)
						Object.modifyValue(stadester_sums, geocodes[x], local_value);
			}
			
			//2. Clamp each raster series to the Stadestér footprint
			for (let s = 0; s < raster_series.length; s++) {
				let input_folder = raster_series[s][0];
				let output_folder = raster_series[s][1];
				let file_prefix = raster_series[s][2];
				let series_key = raster_series[s][3];
				
				let backcalc_path = `${input_folder}${file_prefix}_${year}.png`;
				let clamped_output_path = `${output_folder}${file_prefix}_${year}.png`;
				
				if (!fs.existsSync(backcalc_path)) continue;
				if (!overwrite && fs.existsSync(clamped_output_path)) continue;
				
				let backcalc_raster = GeoPNG.loadNumberRasterImage(backcalc_path, {
					format: "float32"
				});
				
				//Compute national backcalc sums over populated pixels only
				let backcalc_sums = {};
				for (let i = 0; i < backcalc_raster.data.length; i++) {
					if (stadester_raster.data[i] <= 0) continue;
					
					let local_value = backcalc_raster.data[i];
					if (isNaN(local_value) || local_value <= 0) continue;
					
					let byte_index = i * 4;
					let colour_key = [
						geocode_raster.data[byte_index],
						geocode_raster.data[byte_index + 1],
						geocode_raster.data[byte_index + 2]
					].join(",");
					let geocodes = colour_to_geocode[colour_key];
					
					if (geocodes)
						for (let x = 0; x < geocodes.length; x++)
							Object.modifyValue(backcalc_sums, geocodes[x], local_value);
				}
				
				//Determine per-region clamping mode: rescale existing footprint, or inject
				//at the national crude rate where the base has no footprint but population exists
				let region_scalars = {};
				let region_rates = {};
				
				Object.iterate(geocode_obj, (geocode, data) => {
					let in_domain = true;
					if (data.domain) {
						if (year_num < data.domain[0] || year_num > data.domain[1]) {
							in_domain = false;
						}
					}
					if (!in_domain) return;
					
					let hmd_code = geocode.split(".")[0];
					let local_hmd_total = hmd_series[series_key][hmd_code]?.[year];
					//Spline overshoot can yield negatives; clamp to zero
					local_hmd_total = (local_hmd_total !== undefined && local_hmd_total > 0) ? local_hmd_total : 0;
					if (local_hmd_total <= 0) return;
					
					let local_backcalc_sum = backcalc_sums[geocode] || 0;
					let local_stadester_pop = stadester_sums[geocode] || 0;
					
					if (local_backcalc_sum > 0) {
						//Scenario A: rescale the populated footprint to hit HMD totals exactly
						region_scalars[geocode] = local_hmd_total / local_backcalc_sum;
					} else if (local_stadester_pop > 0) {
						//Scenario B: no backcalculated footprint; inject at the national crude rate
						region_rates[geocode] = local_hmd_total / local_stadester_pop;
					}
				});
				
				GeoPNG.saveNumberRasterImage({
					file_path: clamped_output_path,
					format: "float32",
					width: stadester_raster.width,
					height: stadester_raster.height,
					function: (local_index) => {
						let local_stadester_pop = stadester_raster.data[local_index];
						
						//If Stadester explicitly states nobody lives here, strict clamp to 0
						if (local_stadester_pop <= 0) return 0;
						
						let local_backcalc_value = backcalc_raster.data[local_index];
						if (isNaN(local_backcalc_value)) local_backcalc_value = 0;
						
						let byte_index = local_index * 4;
						let colour_key = [
							geocode_raster.data[byte_index],
							geocode_raster.data[byte_index + 1],
							geocode_raster.data[byte_index + 2]
						].join(",");
						let geocodes = colour_to_geocode[colour_key];
						
						if (geocodes)
							for (let x = 0; x < geocodes.length; x++) {
								let local_geocode = geocodes[x];
								
								if (region_scalars[local_geocode] !== undefined)
									return local_backcalc_value * region_scalars[local_geocode];
								if (region_rates[local_geocode] !== undefined)
									return local_stadester_pop * region_rates[local_geocode];
							}
						
						return 0; //No HMD coverage; partial coverage natively resolves to zero pixels
					}
				});
				
				console.log(`- Saved HMD clamped raster: ${clamped_output_path}`);
				await Blacktraffic.yield();
			}
		}
	}
	
	static async processRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		if (!options.exclude) options.exclude = [];
		
		//Ensure all output directories exist
		let all_folders = [
			this.intermediate_backcalculated_births_folder,
			this.intermediate_backcalculated_female_deaths_folder,
			this.intermediate_backcalculated_male_deaths_folder,
			this.output_crude_births_folder,
			this.output_female_crude_deaths_folder,
			this.output_male_crude_deaths_folder
		];
		for (let i = 0; i < all_folders.length; i++)
			if (!fs.existsSync(all_folders[i])) fs.mkdirSync(all_folders[i], { recursive: true });
		
		//Execute steps sequentially unless skipped
		if (!options.exclude.includes("A")) await this.A_getHMDGroups();
		if (!options.exclude.includes("B")) await this.B_generateHMDRasters(options);
		if (!options.exclude.includes("C")) await this.C_clampToStadester(options);
	}
};