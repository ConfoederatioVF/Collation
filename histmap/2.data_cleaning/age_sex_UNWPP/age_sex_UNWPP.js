global.age_sex_UNWPP = class {
	static bf = `${h2}/age_sex_UNWPP/`;
	static input_female_csv = `${h1}/age_sex_UNWPP/female_age_cohorts.csv`;
	static input_male_csv = `${h1}/age_sex_UNWPP/male_age_cohorts.csv`;
	static intermediate_worldpop_backcalculated = `${this.bf}/1.backcalculated_from_worldpop/`;
	static output_clamped_to_stadester = `${this.bf}/2.clamped_to_stadester/`;
	static unwpp_years = [1950, 1951, 1952, 1953, 1954, 1955, 1956, 1957, 1958, 1959, 1960, 1961, 1962, 1963, 1964, 1965, 1966, 1967, 1968, 1969, 1970, 1971, 1972, 1973, 1974, 1975, 1976, 1977, 1978, 1979, 1980, 1981, 1982, 1983, 1984, 1985, 1986, 1987, 1988, 1989, 1990, 1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020];
	
	static async A_getUNWPPGroups () {
		//Declare local instance variables
		let unwpp_data = {};
		
		//Load the CSVs using the provided utility
		let female_csv = File.loadCSVAsArray(this.input_female_csv, { delimiter: ";" });
		let male_csv = File.loadCSVAsArray(this.input_male_csv, { delimiter: ";" });
		
		//Helper function to parse UNWPP strings and multiply by 1000
		const parseUNNumber = function (val) {
			if (!val) return 0;
			return Number(val.toString().replace(/\s/g, '')) * 1000;
		};
		
		//Helper function to aggregate 1-year columns into flat WorldPop cohorts (f_00, f_01, etc.)
		const processRowToCohorts = function (row, prefix) {
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
		
		//Process Female Data
		for (let i = 0; i < female_csv.length; i++) {
			let row = female_csv[i];
			let iso3 = row["ISO3 Alpha-code"];
			let year = row["Year"] ? row["Year"].toString().trim() : null;
			
			if (iso3 && year) {
				if (!unwpp_data[iso3]) unwpp_data[iso3] = {};
				if (!unwpp_data[iso3][year]) unwpp_data[iso3][year] = {};
				Object.assign(unwpp_data[iso3][year], processRowToCohorts(row, "f_"));
			}
		}
		
		//Process Male Data
		for (let i = 0; i < male_csv.length; i++) {
			let row = male_csv[i];
			let iso3 = row["ISO3 Alpha-code"];
			let year = row["Year"] ? row["Year"].toString().trim() : null;
			
			if (iso3 && year) {
				if (!unwpp_data[iso3]) unwpp_data[iso3] = {};
				if (!unwpp_data[iso3][year]) unwpp_data[iso3][year] = {};
				Object.assign(unwpp_data[iso3][year], processRowToCohorts(row, "m_"));
			}
		}

		//Empirical Prior Imputation for Zero-Valued Cohorts (due to UN reporting in thousands)
		let all_cohort_keys = [];
		let age_groups = ["00", "01"];
		for (let i = 5; i <= 80; i += 5) age_groups.push(i.toString().padStart(2, "0"));
		for (let i = 0; i < age_groups.length; i++) {
			all_cohort_keys.push(`f_${age_groups[i]}`);
			all_cohort_keys.push(`m_${age_groups[i]}`);
		}

		let global_cohort_sums = {};
		let global_year_totals = {};

		Object.iterate(unwpp_data, (iso, year_obj) => {
			Object.iterate(year_obj, (year, cohort_obj) => {
				if (!global_cohort_sums[year]) {
					global_cohort_sums[year] = {};
					global_year_totals[year] = 0;
					for (let c = 0; c < all_cohort_keys.length; c++)
						global_cohort_sums[year][all_cohort_keys[c]] = 0;
				}

				for (let c = 0; c < all_cohort_keys.length; c++) {
					let val = cohort_obj[all_cohort_keys[c]] || 0;
					global_cohort_sums[year][all_cohort_keys[c]] += val;
					global_year_totals[year] += val;
				}
			});
		});

		//1. Impute zero cohorts in countries with population > 0 via empirical Bayesian prior shrinkage and conserve country totals
		Object.iterate(unwpp_data, (iso, year_obj) => {
			Object.iterate(year_obj, (year, cohort_obj) => {
				let country_pop = 0;
				let has_zero = false;

				for (let c = 0; c < all_cohort_keys.length; c++) {
					let val = cohort_obj[all_cohort_keys[c]] || 0;
					country_pop += val;
					if (val <= 0) has_zero = true;
				}

				if (country_pop > 0 && has_zero) {
					let adjusted_pop = 0;
					let total_year_pop = global_year_totals[year] || 1;

					for (let c = 0; c < all_cohort_keys.length; c++) {
						let key = all_cohort_keys[c];
						let val = cohort_obj[key] || 0;
						if (val <= 0) {
							let global_share = (global_cohort_sums[year]?.[key] || 0) / total_year_pop;
							if (global_share <= 0) global_share = 1 / all_cohort_keys.length;
							cohort_obj[key] = Math.min(400, Math.max(5, global_share * country_pop));
						}
						adjusted_pop += cohort_obj[key];
					}

					//Mass conservation: re-normalise cohorts to preserve country_pop exactly
					if (adjusted_pop > 0) {
						let scale = country_pop / adjusted_pop;
						for (let c = 0; c < all_cohort_keys.length; c++)
							cohort_obj[all_cohort_keys[c]] *= scale;
					}
				}
			});
		});

		//2. Impute non-zero plausible cohorts for micro-nations and unrecorded country-years (where country_pop is 0)
		Object.iterate(unwpp_data, (iso, year_obj) => {
			//Index years with reported positive populations for this country
			let positive_years = [];
			Object.iterate(year_obj, (y, c_obj) => {
				let sum = 0;
				for (let c = 0; c < all_cohort_keys.length; c++) sum += (c_obj[all_cohort_keys[c]] || 0);
				if (sum > 0) positive_years.push({ pop: sum, year: parseInt(y) });
			});

			Object.iterate(year_obj, (year, cohort_obj) => {
				let country_pop = 0;
				for (let c = 0; c < all_cohort_keys.length; c++) country_pop += (cohort_obj[all_cohort_keys[c]] || 0);

				if (country_pop <= 0) {
					let cur_global = global_year_totals[year] || 1;
					let estimated_pop = 5000;
					let target_year = parseInt(year);

					if (positive_years.length > 0) {
						positive_years.sort((a, b) => Math.abs(a.year - target_year) - Math.abs(b.year - target_year));
						let ref = positive_years[0];
						let ref_global = global_year_totals[ref.year.toString()] || 1;
						estimated_pop = Math.max(100, ref.pop * (cur_global / ref_global));
					} else {
						let g2015 = global_year_totals["2015"] || 1;
						estimated_pop = Math.max(200, 5000 * (cur_global / g2015));
					}

					let total_year_pop = global_year_totals[year] || 1;
					for (let c = 0; c < all_cohort_keys.length; c++) {
						let key = all_cohort_keys[c];
						let global_share = (global_cohort_sums[year]?.[key] || 0) / total_year_pop;
						if (global_share <= 0) global_share = 1 / all_cohort_keys.length;
						cohort_obj[key] = Math.max(1, estimated_pop * global_share);
					}
				}
			});
		});
		
		//Save to the class as a static variable and return
		this.unwpp_data = unwpp_data;
		return unwpp_data;
	}
	
	static async A_generateUNWPPRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;

		//Declare local instance variables
		let unwpp_data = this.unwpp_data || await this.A_getUNWPPGroups();
		let all_worldpop_files = await File.getAllFiles(`${h1}/age_sex_WorldPop/rasters/`);
		let geocode_obj = admin_modern.getISO3ColourcodesObject();
		let geocode_raster = GeoPNG.loadImage(admin_modern.input_geocodes_raster);
		
		//UNWPP historical boundary 1950-2020
		let unwpp_years = (options.years) ? options.years : this.unwpp_years;
		
		//Pre-index pixel indices per ISO code
		let geocode_pixel_indices = {};
		for (let index = 0; index < geocode_raster.data.length / 4; index++) {
			let byte_index = index * 4;
			let r = geocode_raster.data[byte_index];
			let g = geocode_raster.data[byte_index + 1];
			let b = geocode_raster.data[byte_index + 2];
			let colour_key = `${r},${g},${b}`;
			let geocodes = geocode_obj[colour_key];
			if (geocodes) {
				for (let x = 0; x < geocodes.length; x++) {
					let iso = geocodes[x];
					if (!geocode_pixel_indices[iso]) geocode_pixel_indices[iso] = [];
					geocode_pixel_indices[iso].push(index);
				}
			}
		}

		//Establish standard cohort key list
		let age_groups = ["00", "01"];
		for (let i = 5; i <= 80; i += 5) age_groups.push(i.toString().padStart(2, "0"));
		let all_cohort_keys = [];
		for (let i = 0; i < age_groups.length; i++) {
			all_cohort_keys.push(`f_${age_groups[i]}`);
			all_cohort_keys.push(`m_${age_groups[i]}`);
		}

		//Identify base WorldPop rasters with integrity verification
		let cohort_base_rasters = {};
		for (let c = 0; c < all_cohort_keys.length; c++) {
			let c_key = all_cohort_keys[c];
			let match_2015 = all_worldpop_files.find((f) => {
				let b = path.basename(f);
				return (b.includes(`${c_key}_2015_`) || b.includes(`global_${c_key}_2015`));
			});

			let chosen_file = match_2015;
			if (match_2015 && fs.existsSync(match_2015)) {
				let sz = fs.statSync(match_2015).size;
				if (sz < 1000000) chosen_file = null; //Corrupted file guard
			}

			//Fallback to 2016 if 2015 file is missing or corrupted
			if (!chosen_file) {
				let match_2016 = all_worldpop_files.find((f) => {
					let b = path.basename(f);
					return (b.includes(`${c_key}_2016_`) || b.includes(`global_${c_key}_2016`));
				});
				if (match_2016) {
					chosen_file = match_2016;
					console.warn(`[WARN] Using 2016 fallback base raster for cohort ${c_key} due to missing/corrupted 2015.`);
				}
			}

			if (chosen_file) cohort_base_rasters[c_key] = chosen_file;
		}
		
		//Iterate over cohort keys
		let cohorts_to_process = (options.cohorts) ? options.cohorts : all_cohort_keys;
		for (let c = 0; c < cohorts_to_process.length; c++) {
			let local_cohort_key = cohorts_to_process[c];
			let local_file_path = cohort_base_rasters[local_cohort_key];
			if (!local_file_path || !fs.existsSync(local_file_path)) continue;
			
			//1. Load in the base raster and sum by ISO using pre-indexed pixels
			let local_base_sums = {};
			let local_base_raster = GeoPNG.loadNumberRasterImage(local_file_path, {
				format: "float32"
			});
			
			Object.iterate(geocode_pixel_indices, (iso, indices) => {
				let sum = 0;
				for (let k = 0; k < indices.length; k++) sum += local_base_raster.data[indices[k]];
				local_base_sums[iso] = sum;
			});
			
			console.log(`- Loaded base spatial mask for cohort: ${local_cohort_key} from ${path.basename(local_file_path)}`);
			
			//2. Backcalculate iteration over the 1950-2020 time frame
			for (let y = 0; y < unwpp_years.length; y++) {
				let local_year = unwpp_years[y];
				let local_output_file = `${this.intermediate_worldpop_backcalculated}global_${local_cohort_key}_${local_year}.png`;
				
				if (!overwrite && fs.existsSync(local_output_file)) continue;
				
				//Determine specific scaling ratio mapping
				let local_scalars = {};
				Object.iterate(local_base_sums, (local_iso, local_base_pop) => {
					let local_actual_pop = unwpp_data[local_iso]?.[local_year]?.[local_cohort_key];
					
					if (local_actual_pop !== undefined) {
						local_scalars[local_iso] = (local_base_pop !== 0) ? (local_actual_pop / local_base_pop) : 0;
					} else {
						//If a state goes unrecognized (i.e. micro-nations), assume stable population and copy base natively via 1.0 scalar
						local_scalars[local_iso] = 1;
					}
				});
				
				//3. Scale and save raster
				let scaled_buffer = new Float32Array(local_base_raster.data);
				Object.iterate(geocode_pixel_indices, (iso, indices) => {
					let scalar = local_scalars[iso];
					if (scalar !== undefined && scalar !== 1) {
						for (let k = 0; k < indices.length; k++) {
							scaled_buffer[indices[k]] *= scalar;
						}
					}
				});
				
				GeoPNG.saveNumberRasterImage({
					file_path: local_output_file,
					format: "float32",
					height: local_base_raster.height,
					width: local_base_raster.width,
					function: (local_index) => scaled_buffer[local_index]
				});
				
				console.log(`Processed backcalculation: ${local_output_file}`);
				await Blacktraffic.yield();
			}
		}
	}
	
	static async B_clampToStadester (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};

		//Declare local instance variables
		let unwpp_data = this.unwpp_data || await this.A_getUNWPPGroups();
		let geocode_obj = admin_modern.getISO3ColourcodesObject();
		let geocode_raster = GeoPNG.loadImage(admin_modern.input_geocodes_raster);
		
		//Establish temporal bounds (1950 - 2020)
		let unwpp_years = (options.years) ? options.years : this.unwpp_years;
		
		//Generate standard WorldPop 1/5-year cohort keys programmatically
		let age_groups = ["00", "01"];
		for (let i = 5; i <= 80; i += 5) age_groups.push(i.toString().padStart(2, "0"));
		
		let all_cohorts = [];
		for (let i = 0; i < age_groups.length; i++) {
			all_cohorts.push(`f_${age_groups[i]}`);
			all_cohorts.push(`m_${age_groups[i]}`);
		}
		
		//Iterate over temporal bounds
		for (let y = 0; y < unwpp_years.length; y++) {
			let local_year = unwpp_years[y];
			let pop_path = `${population_Stadester.input_popc_folder}stadester_population_${local_year}.png`;
			
			//Guard clause if no Stadestér temporal anchor exists for this year
			if (!fs.existsSync(pop_path)) continue;
			
			console.log(`Processing Stadester dasymetric clamping for year: ${local_year}`);
			
			//Pre-calculate national demographic fractions for empty-pixel fallbacks
			let national_fractions = {};
			Object.iterate(unwpp_data, (local_iso, local_year_data) => {
				let local_data = local_year_data[local_year];
				if (!local_data) return;
				
				let local_total = 0;
				for (let c = 0; c < all_cohorts.length; c++)
					local_total += (local_data[all_cohorts[c]] || 0);
				
				if (local_total > 0) {
					national_fractions[local_iso] = {};
					for (let c = 0; c < all_cohorts.length; c++) {
						let cohort_key = all_cohorts[c];
						national_fractions[local_iso][cohort_key] = (local_data[cohort_key] || 0) / local_total;
					}

					//Infant Biological Sex Ratio Sanity Check: enforce M/F within [0.90, 1.20]
					let f_00_frac = national_fractions[local_iso]["f_00"] || 0;
					let m_00_frac = national_fractions[local_iso]["m_00"] || 0;
					if (f_00_frac > 0) {
						let srb = m_00_frac / f_00_frac;
						if (srb < 0.90 || srb > 1.20) {
							national_fractions[local_iso]["m_00"] = f_00_frac * 1.05;
							let re_sum = 0;
							for (let c = 0; c < all_cohorts.length; c++)
								re_sum += national_fractions[local_iso][all_cohorts[c]];
							if (re_sum > 0) {
								for (let c = 0; c < all_cohorts.length; c++)
									national_fractions[local_iso][all_cohorts[c]] /= re_sum;
							}
						}
					}
				}
			});
			
			//1. Load Stadester popc anchor raster
			let stadester_raster = GeoPNG.loadNumberRasterImage(pop_path, {
				format: "float32"
			});
			
			//2. Dasymetric Cohort Scaling via GeoPNG framework
			await GeoPNG.dasymetricCohortScale({
				anchor_raster: stadester_raster,
				cohort_keys: all_cohorts,
				cohort_path_function: (cohort_key) => `${this.intermediate_worldpop_backcalculated}global_${cohort_key}_${local_year}.png`,
				geocode_obj: geocode_obj,
				geocode_raster: geocode_raster,
				national_fractions: national_fractions,
				output_path_function: (cohort_key) => `${this.output_clamped_to_stadester}global_${cohort_key}_${local_year}.png`
			});
			
			console.log(`- Saved clamped demographic cohorts for year ${local_year}`);
			await Blacktraffic.yield();
		}
	}
	
	static async processRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		if (!options.exclude) options.exclude = [];
		
		//Process to Stadestér
		if (!options.exclude.includes("A")) await this.A_generateUNWPPRasters(options);
		if (!options.exclude.includes("B")) await this.B_clampToStadester(options);
	}
};