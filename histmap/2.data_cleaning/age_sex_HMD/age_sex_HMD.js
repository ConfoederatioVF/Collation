global.age_sex_HMD = class {
	static bf = `${h2}/age_sex_HMD/`
	static input_HMD_population_file = `${h1}/age_sex_HMD/population/Population.txt`;
	static intermediate_unwpp_backcalculated = `${this.bf}/1.backcalculated_from_UNWPP/`;
	static output_clamped_to_stadester = `${this.bf}/2.clamped_to_stadester/`;
	
	static A_getHMDObject () {
		//Declare local instance variables
		let raw_text = fs.readFileSync(this.input_HMD_population_file, "utf8");
		let lines = raw_text.split(/\r?\n/);
		let return_obj = {};
		
		//Iterate over lines
		for (let i = 0; i < lines.length; i++) {
			let line = lines[i].trim();
			
			//Skip empty lines, file headers, or table headers
			if (!line || line.startsWith("Population") || line.startsWith("PopName")) continue;
			
			//Split columns by 1-or-more whitespace characters
			let cols = line.split(/\s+/);
			if (cols.length < 5) continue; //Guard clause: ensure row has at least PopName, Year, Age, Female, Male
			
			let pop_name = cols[0];
			let year = cols[1];
			let age_str = cols[2];
			
			//Parse floats (HMD numbers have decimals and no thousands separators)
			let female = parseFloat(cols[3]) || 0;
			let male = parseFloat(cols[4]) || 0;
			
			//Parse age, seamlessly handling HMD formatting like "110+"
			let parsed_age = parseInt(age_str);
			if (isNaN(parsed_age)) continue;
			
			//Determine WorldPop bucket equivalent
			let bucket;
			if (parsed_age === 0) {
				bucket = "00";
			} else if (parsed_age >= 1 && parsed_age <= 4) {
				bucket = "01";
			} else if (parsed_age >= 80) {
				bucket = "80"; //Groups 80 to 110+
			} else {
				//Groups 5, 10, 15... etc.
				bucket = String(Math.floor(parsed_age / 5) * 5).padStart(2, "0");
			}
			
			//Initialise the object tree for Geocode -> Year
			if (!return_obj[pop_name]) return_obj[pop_name] = {};
			if (!return_obj[pop_name][year]) return_obj[pop_name][year] = {};
			
			let year_obj = return_obj[pop_name][year];
			let f_key = `f_${bucket}`;
			let m_key = `m_${bucket}`;
			
			//Add populations to their respective cohorts
			if (!year_obj[f_key]) year_obj[f_key] = 0;
			year_obj[f_key] += female;
			
			if (!year_obj[m_key]) year_obj[m_key] = 0;
			year_obj[m_key] += male;
		}
		
		//Return statement
		return return_obj;
	}
	
	static async A_generateHMDRasters () {
		//Declare local instance variables
		let raw_hmd_data = this.A_getHMDObject();
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
		
		//Pivot and cubicSplineInterpolate HMD data to match HYDE years exactly
		let hmd_data = {};
		Object.iterate(raw_hmd_data, (geocode, year_obj) => {
			let cohorts_series = {};
			Object.iterate(year_obj, (yr, cohorts) => {
				Object.iterate(cohorts, (c_key, c_val) => {
					if (!cohorts_series[c_key]) cohorts_series[c_key] = {};
					cohorts_series[c_key][yr] = c_val;
				});
			});
			
			hmd_data[geocode] = {};
			Object.iterate(cohorts_series, (c_key, series) => {
				let interp_series = Object.cubicSplineInterpolation(series, { years: hyde_years });
				Object.iterate(interp_series, (h_yr, h_val) => {
					if (!hmd_data[geocode][h_yr]) hmd_data[geocode][h_yr] = {};
					hmd_data[geocode][h_yr][c_key] = h_val;
				});
			});
		});
		
		//Generate standard WorldPop 1/5-year cohort keys
		let age_groups = ["00", "01"];
		for (let i = 5; i <= 80; i += 5) age_groups.push(i.toString().padStart(2, "0"));
		
		let all_cohorts = [];
		for (let i = 0; i < age_groups.length; i++) {
			all_cohorts.push(`f_${age_groups[i]}`);
			all_cohorts.push(`m_${age_groups[i]}`);
		}
		
		//Iterate over all cohorts
		for (let c = 0; c < all_cohorts.length; c++) {
			let cohort = all_cohorts[c];
			let base_1950_path = `${age_sex_UNWPP.intermediate_worldpop_backcalculated}global_${cohort}_1950.png`;
			
			if (!fs.existsSync(base_1950_path)) continue;
			
			let base_sums = {};
			let base_raster = GeoPNG.loadNumberRasterImage(base_1950_path, {
				format: "float32"
			});
			
			//1. Calculate the 1950 starting population mass for each HMD region
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
			
			//2. Backcalculate strictly over specified HYDE temporal boundaries
			for (let y = 0; y < hyde_years.length; y++) {
				let year = hyde_years[y];
				let year_num = parseInt(year);
				
				//GUARD CLAUSE: HMD is strictly for historical backcalculation prior to the UNWPP era.
				if (year_num >= 1950) continue;
				
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
					
					if (in_domain && hmd_data[hmd_code] && hmd_data[hmd_code][year]) {
						let target_pop = hmd_data[hmd_code][year][cohort] || 0;
						let base_pop = base_sums[geocode] || 0;
						
						if (target_pop > 0) {
							scalars[geocode] = (base_pop > 0) ? (target_pop / base_pop) : 0;
							has_data = true;
						} else {
							scalars[geocode] = 0;
						}
					} else {
						scalars[geocode] = 0;
					}
				});
				
				//If no countries have data for this time period, do not produce an output raster
				if (!has_data) continue;
				
				let output_path = `${this.intermediate_unwpp_backcalculated}global_${cohort}_${year}.png`;
				
				//3. Dasymetrically save the historical raster
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
	
	static async B_clampToStadester () {
		//Declare local instance variables
		let raw_hmd_data = this.A_getHMDObject();
		let geocode_obj = admin_modern.getHMDColourcodesObject();
		let geocode_raster = GeoPNG.loadImage(admin_modern.input_hmd_raster);
		let hyde_years = landuse_HYDE.sorted_hyde_years;
		
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
		
		//Interpolate HMD data exactly as above to compute correct fractions
		let hmd_data = {};
		Object.iterate(raw_hmd_data, (geocode, year_obj) => {
			let cohorts_series = {};
			Object.iterate(year_obj, (yr, cohorts) => {
				Object.iterate(cohorts, (c_key, c_val) => {
					if (!cohorts_series[c_key]) cohorts_series[c_key] = {};
					cohorts_series[c_key][yr] = c_val;
				});
			});
			hmd_data[geocode] = {};
			Object.iterate(cohorts_series, (c_key, series) => {
				let interp_series = Object.cubicSplineInterpolation(series, { years: hyde_years });
				Object.iterate(interp_series, (h_yr, h_val) => {
					if (!hmd_data[geocode][h_yr]) hmd_data[geocode][h_yr] = {};
					hmd_data[geocode][h_yr][c_key] = h_val;
				});
			});
		});
		
		let age_groups = ["00", "01"];
		for (let i = 5; i <= 80; i += 5) age_groups.push(i.toString().padStart(2, "0"));
		let all_cohorts = [];
		for (let i = 0; i < age_groups.length; i++) {
			all_cohorts.push(`f_${age_groups[i]}`);
			all_cohorts.push(`m_${age_groups[i]}`);
		}
		
		for (let y = 0; y < hyde_years.length; y++) {
			let year = hyde_years[y];
			let year_num = parseInt(year);
			
			//GUARD CLAUSE: HMD is strictly for historical backcalculation prior to the UNWPP era.
			if (year_num >= 1950) continue;
			
			let pop_path = `${population_Stadester.input_popc_folder}stadester_population_${year}.png`;
			
			if (!fs.existsSync(pop_path)) continue;
			
			let has_any_cohorts = false;
			for (let c = 0; c < all_cohorts.length; c++) {
				if (fs.existsSync(`${this.intermediate_unwpp_backcalculated}global_${all_cohorts[c]}_${year}.png`)) {
					has_any_cohorts = true;
					break;
				}
			}
			if (!has_any_cohorts) continue;
			
			console.log(`Processing Stadester dasymetric clamping for HMD year: ${year}`);
			
			let national_fractions = {};
			Object.iterate(geocode_obj, (geocode, data) => {
				let hmd_code = geocode.split(".")[0];
				let local_data = hmd_data[hmd_code]?.[year];
				if (!local_data) return;
				
				let local_total = 0;
				for (let c = 0; c < all_cohorts.length; c++) {
					let val = local_data[all_cohorts[c]];
					if (val > 0) local_total += val;
				}
				
				if (local_total > 0) {
					national_fractions[geocode] = {};
					for (let c = 0; c < all_cohorts.length; c++) {
						let val = local_data[all_cohorts[c]];
						national_fractions[geocode][all_cohorts[c]] = (val > 0 ? val : 0) / local_total;
					}
				}
			});
			
			let stadester_raster = GeoPNG.loadNumberRasterImage(pop_path, { format: "float32" });
			let total_backcalculated = new Float32Array(stadester_raster.width * stadester_raster.height);
			
			for (let c = 0; c < all_cohorts.length; c++) {
				let backcalc_path = `${this.intermediate_unwpp_backcalculated}global_${all_cohorts[c]}_${year}.png`;
				
				if (fs.existsSync(backcalc_path)) {
					let local_cohort_raster = GeoPNG.loadNumberRasterImage(backcalc_path, { format: "float32" });
					for (let i = 0; i < total_backcalculated.length; i++) {
						total_backcalculated[i] += local_cohort_raster.data[i];
					}
				}
			}
			
			for (let c = 0; c < all_cohorts.length; c++) {
				let cohort_key = all_cohorts[c];
				let backcalc_path = `${this.intermediate_unwpp_backcalculated}global_${cohort_key}_${year}.png`;
				let clamped_output_path = `${this.output_clamped_to_stadester}global_${cohort_key}_${year}.png`;
				
				if (!fs.existsSync(backcalc_path)) continue;
				
				let local_cohort_raster = GeoPNG.loadNumberRasterImage(backcalc_path, { format: "float32" });
				
				GeoPNG.saveNumberRasterImage({
					file_path: clamped_output_path,
					format: "float32",
					width: stadester_raster.width,
					height: stadester_raster.height,
					function: (local_index) => {
						let local_statester_pop = stadester_raster.data[local_index];
						if (local_statester_pop <= 0) return 0;
						
						let local_backcalc_total = total_backcalculated[local_index];
						let local_cohort_value = local_cohort_raster.data[local_index];
						
						if (local_backcalc_total > 0) {
							return (local_cohort_value / local_backcalc_total) * local_statester_pop;
						}
						
						let byte_index = local_index * 4;
						let colour_key = [
							geocode_raster.data[byte_index],
							geocode_raster.data[byte_index + 1],
							geocode_raster.data[byte_index + 2]
						].join(",");
						
						let geocodes = colour_to_geocode[colour_key];
						if (geocodes) {
							for (let x = 0; x < geocodes.length; x++) {
								let fraction = national_fractions[geocodes[x]]?.[cohort_key];
								if (fraction !== undefined) {
									return local_statester_pop * fraction;
								}
							}
						}
						
						return 0;
					}
				});
				
				console.log(`- Saved HMD clamped demographic cohort: ${clamped_output_path}`);
				await Blacktraffic.yield();
			}
		}
	}
	
	static async processRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		if (!options.exclude) options.exclude = [];
		
		//Process to Stadestér
		if (!options.exclude.includes("A")) await this.A_generateHMDRasters();
		if (!options.exclude.includes("B")) await this.B_clampToStadester();
	}
};