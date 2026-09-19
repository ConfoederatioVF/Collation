global.births_deaths_UNWPP = class {
	static bf = `${h2}/births_deaths_UNWPP/`;
	static input_female_fertility_csv = `${h1}/births_deaths_UNWPP/fertility_by_maternal_age.csv`;
	static input_female_deaths_csv = `${h1}/births_deaths_UNWPP/deaths_single_age_female.csv`;
	static input_male_deaths_csv = `${h1}/births_deaths_UNWPP/deaths_single_age_male.csv`;
	static intermediate_backcalculated_births_folder = `${this.bf}/0.backcalculated_births/`;
	static intermediate_backcalculated_female_deaths_folder = `${this.bf}/0.backcalculated_female_deaths/`;
	static intermediate_backcalculated_male_deaths_folder = `${this.bf}/0.backcalculated_male_deaths/`;
	static output_crude_births_folder = `${this.bf}/1.crude_births/`;
	static output_female_crude_deaths_folder = `${this.bf}/1.female_crude_deaths/`;
	static output_male_crude_deaths_folder = `${this.bf}/1.male_crude_deaths/`;
	
	/**
	 * Helper function to compute national sums of a number raster via ISO3 geocodes.
	 * @param {Object} arg0_raster - The loaded number raster.
	 * @param {Object} arg1_geocode_obj - The colour-key to ISO3 lookup object.
	 * @param {Object} arg2_geocode_raster - The loaded geocode RGBA raster.
	 * @returns {Object} An object mapping ISO3 codes to raster sums.
	 */
	static _getNationalSums (arg0_raster, arg1_geocode_obj, arg2_geocode_raster) {
		//Convert from parameters
		let raster = arg0_raster;
		let geocode_obj = arg1_geocode_obj;
		let geocode_raster = arg2_geocode_raster;
		
		//Declare local instance variables
		let sums = {};
		
		//Iterate over all pixels and bucket by national geocode
		for (let i = 0; i < raster.data.length; i++) {
			let local_value = raster.data[i];
			
			if (isNaN(local_value) || local_value <= 0) continue;
			
			let byte_index = i * 4;
			let local_colour_key = [
				geocode_raster.data[byte_index],
				geocode_raster.data[byte_index + 1],
				geocode_raster.data[byte_index + 2]
			].join(",");
			let local_geocodes = geocode_obj[local_colour_key];
			
			if (local_geocodes)
				for (let x = 0; x < local_geocodes.length; x++)
					Object.modifyValue(sums, local_geocodes[x], local_value);
		}
		
		//Return statement
		return sums;
	}
	
	/**
	 * Parses the UNWPP fertility and deaths CSVs into national aggregates.
	 * Births are summed across all maternal age cohorts into a crude national total.
	 * Deaths are binned into sex-specific cohorts with female/male totals.
	 * All values are converted from thousands into absolute counts.
	 */
	static async A_getUNWPPGroups () {
		//Declare local instance variables
		let births_data = {};
		let deaths_data = {};
		
		//Load the CSVs using the provided utility
		let fertility_csv = File.loadCSVAsArray(this.input_female_fertility_csv, { delimiter: ";" });
		let female_deaths_csv = File.loadCSVAsArray(this.input_female_deaths_csv, { delimiter: ";" });
		let male_deaths_csv = File.loadCSVAsArray(this.input_male_deaths_csv, { delimiter: ";" });
		
		//Helper function to parse UNWPP strings and multiply by 1000
		let parseUNNumber = function (val) {
			if (!val) return 0;
			return Number(val.toString().replace(/\s/g, '')) * 1000;
		};
		
		//Helper function to aggregate 1-year columns into flat WorldPop cohorts (f_00, f_01, etc.)
		let processRowToCohorts = function (row, prefix) {
			let cohorts = {};
			
			cohorts[`${prefix}00`] = parseUNNumber(row["0"]);
			
			cohorts[`${prefix}01`] = 0;
			for (let i = 1; i <= 4; i++) cohorts[`${prefix}01`] += parseUNNumber(row[i.toString()]);
			
			for (let base = 5; base <= 75; base += 5) {
				let key = base.toString().padStart(2, "0");
				cohorts[`${prefix}${key}`] = 0;
				for (let i = 0; i <= 4; i++) {
					cohorts[`${prefix}${key}`] += parseUNNumber(row[(base + i).toString()]);
				}
			}
			
			cohorts[`${prefix}80`] = 0;
			for (let i = 80; i <= 99; i++) cohorts[`${prefix}80`] += parseUNNumber(row[i.toString()]);
			cohorts[`${prefix}80`] += parseUNNumber(row["100+"]);
			
			return cohorts;
		};
		
		//Process Fertility Data (maternal age cohorts summed into crude national births)
		for (let i = 0; i < fertility_csv.length; i++) {
			let row = fertility_csv[i];
			let iso3 = row["ISO3 Alpha-code"];
			let year = row["Year"] ? row["Year"].toString().trim() : null;
			
			if (iso3 && year) {
				if (!births_data[iso3]) births_data[iso3] = {};
				
				let local_cohorts = processRowToCohorts(row, "f_");
				let local_total = 0;
				Object.iterate(local_cohorts, (local_key, local_value) => {
					local_total += local_value;
				});
				local_cohorts.total = local_total;
				
				births_data[iso3][year] = local_cohorts;
			}
		}
		
		//Process Deaths Data (sex-specific cohorts with female/male totals)
		let ingestDeaths = function (csv, prefix, total_key) {
			for (let i = 0; i < csv.length; i++) {
				let row = csv[i];
				let iso3 = row["ISO3 Alpha-code"];
				let year = row["Year"] ? row["Year"].toString().trim() : null;
				
				if (iso3 && year) {
					if (!deaths_data[iso3]) deaths_data[iso3] = {};
					if (!deaths_data[iso3][year]) deaths_data[iso3][year] = {};
					
					let local_cohorts = processRowToCohorts(row, prefix);
					let local_total = 0;
					Object.iterate(local_cohorts, (local_key, local_value) => {
						local_total += local_value;
					});
					
					Object.assign(deaths_data[iso3][year], local_cohorts);
					deaths_data[iso3][year][total_key] = local_total;
				}
			}
		};
		
		ingestDeaths(female_deaths_csv, "f_", "f_total");
		ingestDeaths(male_deaths_csv, "m_", "m_total");
		
		//Save to the class as static variables and return
		this.births_data = births_data;
		this.deaths_data = deaths_data;
		return { births: births_data, deaths: deaths_data };
	}
	
	/**
	 * Backcalculates births/deaths over the UNWPP domain (1950-2020) using Kummu rasters
	 * as the observed spatial base, scaled to UNWPP national totals. Years inside Kummu's
	 * range (2000-2019) use that year's own raster as the base; out-of-range years
	 * backcalculate from the nearest boundary year (2000 or 2019).
	 *
	 * The ensemble is inherent: Kummu supplies the spatial pattern, UNWPP supplies the
	 * national totals and the male/female death split. This avoids inferring vital events
	 * from population stocks, which migration would distort.
	 *
	 * UNWPP occasionally records literal zeroes for an entire country-year (a known data
	 * glitch on their end, e.g. Estonian female mortality). Each variable is assessed
	 * independently: where UNWPP reports zero or missing data, Kummu crude rates are
	 * held constant and backprojected, with aggregates scaled by national population
	 * change between the base and target years.
	 */
	static async B_backcalculateFromKummu () {
		//Declare local instance variables
		let groups = (this.births_data && this.deaths_data) ? { births: this.births_data, deaths: this.deaths_data } : await this.A_getUNWPPGroups();
		let births_data = groups.births;
		let deaths_data = groups.deaths;
		
		let geocode_obj = admin_modern.getISO3ColourcodesObject();
		let geocode_raster = GeoPNG.loadImage(admin_modern.input_geocodes_raster);
		
		let unwpp_years = age_sex_UNWPP.unwpp_years;
		let kummu_years = births_deaths_Kummu.years;
		let kummu_min_year = kummu_years[0];
		let kummu_max_year = kummu_years[kummu_years.length - 1];
		
		//Base raster cache (ordered iteration means each base is loaded once)
		let current_base_year = null;
		let base_births_raster = null;
		let base_deaths_raster = null;
		let base_births_sums = null;
		let base_deaths_sums = null;
		let base_popc_sums = null;
		
		//Iterate over temporal bounds
		for (let y = 0; y < unwpp_years.length; y++) {
			let local_year = unwpp_years[y];
			
			let births_output_path = `${this.intermediate_backcalculated_births_folder}births_${local_year}.png`;
			let female_deaths_output_path = `${this.intermediate_backcalculated_female_deaths_folder}female_deaths_${local_year}.png`;
			let male_deaths_output_path = `${this.intermediate_backcalculated_male_deaths_folder}male_deaths_${local_year}.png`;
			
			if (fs.existsSync(births_output_path) && fs.existsSync(female_deaths_output_path) && fs.existsSync(male_deaths_output_path)) continue;
			
			//Resolve the Kummu base year: the year itself if in range, else nearest boundary
			let base_year = Math.min(Math.max(local_year, kummu_min_year), kummu_max_year);
			
			//(Re)load base rasters and national sums only when the base year changes
			if (base_year !== current_base_year) {
				let base_births_path = `${births_deaths_Kummu.output_births_folder}births_${base_year}.png`;
				let base_deaths_path = `${births_deaths_Kummu.output_deaths_folder}deaths_${base_year}.png`;
				
				if (!fs.existsSync(base_births_path) || !fs.existsSync(base_deaths_path)) {
					console.warn(`[WARN] Missing Kummu base rasters for base year ${base_year}. Skipping ${local_year}.`);
					current_base_year = null;
					continue;
				}
				
				base_births_raster = GeoPNG.loadNumberRasterImage(base_births_path, { format: "float32" });
				base_deaths_raster = GeoPNG.loadNumberRasterImage(base_deaths_path, { format: "float32" });
				base_births_sums = this._getNationalSums(base_births_raster, geocode_obj, geocode_raster);
				base_deaths_sums = this._getNationalSums(base_deaths_raster, geocode_obj, geocode_raster);
				
				//Load base-year Stadestér population sums for the rate-preserving fallback
				base_popc_sums = {};
				let base_popc_path = `${population_Stadester.input_popc_folder}stadester_population_${base_year}.png`;
				
				if (fs.existsSync(base_popc_path)) {
					let base_popc_raster = GeoPNG.loadNumberRasterImage(base_popc_path, { format: "float32" });
					base_popc_sums = this._getNationalSums(base_popc_raster, geocode_obj, geocode_raster);
				}
				
				current_base_year = base_year;
				
				console.log(`- Loaded Kummu base spatial masks from ${base_year}`);
			}
			
			//Compute target-year Stadestér national population sums for the rate-preserving fallback
			let target_popc_sums = {};
			let target_popc_path = `${population_Stadester.input_popc_folder}stadester_population_${local_year}.png`;
			
			if (fs.existsSync(target_popc_path)) {
				let target_popc_raster = GeoPNG.loadNumberRasterImage(target_popc_path, { format: "float32" });
				target_popc_sums = this._getNationalSums(target_popc_raster, geocode_obj, geocode_raster);
			}
			
			//Helper function to derive the population ratio scalar. This preserves Kummu crude
			//rates per capita while letting aggregates float with national population change
			let getPopulationRatio = function (local_iso) {
				let local_base_pop = base_popc_sums ? base_popc_sums[local_iso] : undefined;
				let local_target_pop = target_popc_sums[local_iso];
				
				if (local_base_pop !== undefined && local_base_pop > 0 && local_target_pop !== undefined)
					return local_target_pop / local_base_pop;
				
				return 1; //No population anchor available; copy base natively
			};
			
			//Helper function to resolve a per-ISO scalar for a single variable. UNWPP zeroes
			//are treated as data glitches (not truth), triggering a constant-rate Kummu
			//backprojection. rate_fraction apportions the shared Kummu deaths base by sex
			//when the fallback fires (1.0 for births, 0.5 per sex for deaths)
			let resolveISOScalar = function (local_iso, local_actual, local_base_sum, rate_fraction) {
				if (local_actual !== undefined && local_actual > 0)
					return (local_base_sum !== 0) ? (local_actual / local_base_sum) : 0;
				
				//Data glitch fallback: hold the Kummu crude rate constant, scale with population
				return getPopulationRatio(local_iso) * rate_fraction;
			};
			
			//Determine per-ISO scaling ratios against UNWPP national aggregates.
			//Each variable (births, female deaths, male deaths) is assessed independently
			let births_scalars = {};
			let female_deaths_scalars = {};
			let male_deaths_scalars = {};
			
			Object.iterate(base_births_sums, (local_iso, local_base_sum) => {
				let local_actual_births = births_data[local_iso]?.[local_year]?.total;
				
				births_scalars[local_iso] = resolveISOScalar(local_iso, local_actual_births, local_base_sum, 1);
			});
			
			Object.iterate(base_deaths_sums, (local_iso, local_base_sum) => {
				let local_female_deaths = deaths_data[local_iso]?.[local_year]?.f_total;
				let local_male_deaths = deaths_data[local_iso]?.[local_year]?.m_total;
				
				female_deaths_scalars[local_iso] = resolveISOScalar(local_iso, local_female_deaths, local_base_sum, 0.5);
				male_deaths_scalars[local_iso] = resolveISOScalar(local_iso, local_male_deaths, local_base_sum, 0.5);
			});
			
			//Helper to resolve a per-pixel scalar from geocodes, passing through unscaled if unrecognised
			let resolveScalar = function (local_index, scalar_obj, fallback) {
				let byte_index = local_index * 4;
				let local_colour_key = [
					geocode_raster.data[byte_index],
					geocode_raster.data[byte_index + 1],
					geocode_raster.data[byte_index + 2]
				].join(",");
				let local_geocodes = geocode_obj[local_colour_key];
				
				if (local_geocodes)
					for (let x = 0; x < local_geocodes.length; x++)
						if (scalar_obj[local_geocodes[x]] !== undefined)
							return scalar_obj[local_geocodes[x]];
				
				return fallback;
			};
			
			//Dump backcalculated rasters to the file system
			GeoPNG.saveNumberRasterImage({
				file_path: births_output_path,
				format: "float32",
				width: base_births_raster.width,
				height: base_births_raster.height,
				function: (local_index) => {
					return base_births_raster.data[local_index] * resolveScalar(local_index, births_scalars, 1);
				}
			});
			GeoPNG.saveNumberRasterImage({
				file_path: female_deaths_output_path,
				format: "float32",
				width: base_deaths_raster.width,
				height: base_deaths_raster.height,
				function: (local_index) => {
					return base_deaths_raster.data[local_index] * resolveScalar(local_index, female_deaths_scalars, 0.5);
				}
			});
			GeoPNG.saveNumberRasterImage({
				file_path: male_deaths_output_path,
				format: "float32",
				width: base_deaths_raster.width,
				height: base_deaths_raster.height,
				function: (local_index) => {
					return base_deaths_raster.data[local_index] * resolveScalar(local_index, male_deaths_scalars, 0.5);
				}
			});
			
			console.log(`Processed backcalculation for ${local_year} (base: ${base_year})`);
			await Blacktraffic.yield();
		}
	}
	
	/**
	 * Clamps backcalculated rasters to the Stadestér population footprint for each year.
	 * Pixels where Stadestér asserts zero population are strictly zeroed; national totals
	 * are re-anchored exactly to UNWPP over the populated footprint. Pixels populated in
	 * the target year but empty in the Kummu base (e.g. shifting coastlines, frontier
	 * settlement) are injected at the national crude rate proportional to local population.
	 *
	 * UNWPP zeroes are data glitches, not truth: where UNWPP records zero or missing
	 * totals for a variable, no re-anchoring occurs and the rate-preserving
	 * backcalculation from step B passes through natively.
	 */
	static async C_clampToStadester () {
		//Declare local instance variables
		let groups = (this.births_data && this.deaths_data) ? { births: this.births_data, deaths: this.deaths_data } : await this.A_getUNWPPGroups();
		let births_data = groups.births;
		let deaths_data = groups.deaths;
		
		let geocode_obj = admin_modern.getISO3ColourcodesObject();
		let geocode_raster = GeoPNG.loadImage(admin_modern.input_geocodes_raster);
		
		let unwpp_years = age_sex_UNWPP.unwpp_years;
		
		//Define the three raster series to clamp: [intermediate_path, output_path, UNWPP total accessor]
		let raster_series = [
			[this.intermediate_backcalculated_births_folder, this.output_crude_births_folder, "births", (iso, year) => births_data[iso]?.[year]?.total],
			[this.intermediate_backcalculated_female_deaths_folder, this.output_female_crude_deaths_folder, "female_deaths", (iso, year) => deaths_data[iso]?.[year]?.f_total],
			[this.intermediate_backcalculated_male_deaths_folder, this.output_male_crude_deaths_folder, "male_deaths", (iso, year) => deaths_data[iso]?.[year]?.m_total]
		];
		
		//Iterate over temporal bounds
		for (let y = 0; y < unwpp_years.length; y++) {
			let local_year = unwpp_years[y];
			let pop_path = `${population_Stadester.input_popc_folder}stadester_population_${local_year}.png`;
			
			//Guard clause if no Stadestér temporal anchor exists for this year
			if (!fs.existsSync(pop_path)) continue;
			
			console.log(`Processing Stadester clamping of births/deaths for year: ${local_year}`);
			
			//1. Load Stadester popc anchor raster and compute national population sums
			let stadester_raster = GeoPNG.loadNumberRasterImage(pop_path, {
				format: "float32"
			});
			let stadester_sums = this._getNationalSums(stadester_raster, geocode_obj, geocode_raster);
			
			//2. Clamp each raster series to the Stadestér footprint
			for (let s = 0; s < raster_series.length; s++) {
				let input_folder = raster_series[s][0];
				let output_folder = raster_series[s][1];
				let file_prefix = raster_series[s][2];
				let total_accessor = raster_series[s][3];
				
				let backcalc_path = `${input_folder}${file_prefix}_${local_year}.png`;
				let clamped_output_path = `${output_folder}${file_prefix}_${local_year}.png`;
				
				if (!fs.existsSync(backcalc_path)) continue;
				if (fs.existsSync(clamped_output_path)) continue;
				
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
					let local_colour_key = [
						geocode_raster.data[byte_index],
						geocode_raster.data[byte_index + 1],
						geocode_raster.data[byte_index + 2]
					].join(",");
					let local_geocodes = geocode_obj[local_colour_key];
					
					if (local_geocodes)
						for (let x = 0; x < local_geocodes.length; x++)
							Object.modifyValue(backcalc_sums, local_geocodes[x], local_value);
				}
				
				//Determine per-ISO clamping mode: rescale existing footprint, or distribute
				//nationally where the backcalculation has no footprint but population exists
				let iso_scalars = {};
				let iso_rates = {};
				
				Object.iterate(stadester_sums, (local_iso, local_stadester_pop) => {
					let local_unwpp_total = total_accessor(local_iso, local_year.toString());
					let local_backcalc_sum = backcalc_sums[local_iso] || 0;
					
					//Zero/missing UNWPP totals are data glitches, not truth: skip re-anchoring
					//and let the rate-preserving backcalculation pass through
					if (local_unwpp_total === undefined || local_unwpp_total <= 0) return;
					
					if (local_backcalc_sum > 0) {
						//Scenario A: rescale the populated footprint to hit UNWPP totals exactly
						iso_scalars[local_iso] = local_unwpp_total / local_backcalc_sum;
					} else if (local_stadester_pop > 0) {
						//Scenario B: no backcalculated footprint; distribute at the national crude rate
						iso_rates[local_iso] = local_unwpp_total / local_stadester_pop;
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
						let local_colour_key = [
							geocode_raster.data[byte_index],
							geocode_raster.data[byte_index + 1],
							geocode_raster.data[byte_index + 2]
						].join(",");
						let local_geocodes = geocode_obj[local_colour_key];
						
						if (local_geocodes)
							for (let x = 0; x < local_geocodes.length; x++) {
								let local_iso = local_geocodes[x];
								
								if (iso_scalars[local_iso] !== undefined)
									return local_backcalc_value * iso_scalars[local_iso];
								if (iso_rates[local_iso] !== undefined)
									return local_stadester_pop * iso_rates[local_iso];
							}
						
						return local_backcalc_value; //Unrecognised/glitch pixels pass through
					}
				});
				
				console.log(`- Saved clamped raster: ${clamped_output_path}`);
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
		if (!options.exclude.includes("A")) await this.A_getUNWPPGroups();
		if (!options.exclude.includes("B")) await this.B_backcalculateFromKummu();
		if (!options.exclude.includes("C")) await this.C_clampToStadester();
	}
};