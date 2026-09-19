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
		
		//Save to the class as a static variable and return
		this.unwpp_data = unwpp_data;
		return unwpp_data;
	}
	
	static async A_generateUNWPPRasters () {
		//Declare local instance variables
		let unwpp_data = this.unwpp_data || await this.A_getUNWPPGroups();
		let all_worldpop_files = await File.getAllFiles(`${h1}/age_sex_WorldPop/rasters/`);
		let geocode_obj = admin_modern.getISO3ColourcodesObject();
		let geocode_raster = GeoPNG.loadImage(admin_modern.input_geocodes_raster);
		
		//UNWPP historical boundary 1950-2020
		let unwpp_years = this.unwpp_years;
		
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
		
		//Iterate over all_worldpop_files
		for (let i = 0; i < all_worldpop_files.length; i++) {
			let local_file_path = all_worldpop_files[i];
			let local_basename = path.basename(local_file_path);
			
			//We strictly want to grab the 2015 rasters to use as spatial bases
			if (!local_basename.includes("_2015_")) continue;
			
			//Regex match for cohort, e.g., matching "f_00" or "m_80"
			let cohort_match = local_basename.match(/(f|m)_([0-9]{2})_2015/);
			if (!cohort_match) continue;
			
			let local_cohort_key = `${cohort_match[1]}_${cohort_match[2]}`;
			
			//1. Load in the 2015 base raster and sum by ISO using pre-indexed pixels
			let local_base_sums = {};
			let local_base_raster = GeoPNG.loadNumberRasterImage(local_file_path, {
				format: "float32"
			});
			
			Object.iterate(geocode_pixel_indices, (iso, indices) => {
				let sum = 0;
				for (let k = 0; k < indices.length; k++) sum += local_base_raster.data[indices[k]];
				local_base_sums[iso] = sum;
			});
			
			console.log(`- Loaded base spatial mask for cohort: ${local_cohort_key}`);
			
			//2. Backcalculate iteration over the 1950-2020 time frame
			for (let y = 0; y < unwpp_years.length; y++) {
				let local_year = unwpp_years[y];
				let local_output_file = `${this.intermediate_worldpop_backcalculated}global_${local_cohort_key}_${local_year}.png`;
				
				if (fs.existsSync(local_output_file)) continue;
				
				//Determine specific scaling ratio mapping
				let local_scalars = {};
				Object.iterate(local_base_sums, (local_iso, local_2015_pop) => {
					let local_actual_pop = unwpp_data[local_iso]?.[local_year]?.[local_cohort_key];
					
					if (local_actual_pop !== undefined) {
						local_scalars[local_iso] = (local_2015_pop !== 0) ? (local_actual_pop / local_2015_pop) : 0;
					} else {
						//If a state goes unrecognized (i.e. micro-nations), assume stable population and copy 2015 natively via 1.0 scalar
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
	
	static async B_clampToStadester () {
		//Declare local instance variables
		let unwpp_data = this.unwpp_data || await this.A_getUNWPPGroups();
		let geocode_obj = admin_modern.getISO3ColourcodesObject();
		let geocode_raster = GeoPNG.loadImage(admin_modern.input_geocodes_raster);
		
		//Establish temporal bounds (1950 - 2020)
		let unwpp_years = this.unwpp_years;
		
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
		if (!options.exclude.includes("A")) await this.A_generateUNWPPRasters();
		if (!options.exclude.includes("B")) await this.B_clampToStadester();
	}
};