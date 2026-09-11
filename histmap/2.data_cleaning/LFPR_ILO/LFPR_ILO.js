global.LFPR_ILO = class {
	static input_lfpr_age_sex_csv = `${h1}/LFPR_ILO/lfpr_age_sex.csv`;
	static output_masks_folder = `${h1}/LFPR_ILO/masks/`;
	
	/**
	 * Parses the ILOSTAT LFPR CSV file, extracting the 10-year bands
	 * and formatting them specifically for working-age cohorts (15+).
	 */
	static A_getILOLocalObject () {
		// Use the native framework loader to bypass raw text parsing issues
		let csv_array = File.loadCSVAsArray(this.input_lfpr_age_sex_csv, { delimiter: "," });
		let return_obj = {};
		let min_year = Infinity; // Anchors interpolation bounds
		
		for (let i = 0; i < csv_array.length; i++) {
			// Extract columns dynamically (guarantees we hit the exact data regardless of headers)
			let cols = Object.values(csv_array[i]);
			if (cols.length < 8) continue;
			
			// Extract and heavily sanitize all strings
			let country = (cols[0] || "").toString().trim();
			let sex_str = (cols[3] || "").toString().trim();
			let age_str = (cols[4] || "").toString().trim();
			let edu_str = (cols[5] || "").toString().trim();
			let year = parseInt(cols[6]);
			let value = parseFloat(cols[7]); // % Labour force participation
			
			// Strict Guard Clauses
			if (isNaN(year) || isNaN(value)) continue;
			if (!edu_str.includes("Total")) continue; // Avoids duplicate ISCED-11 brackets
			if (sex_str !== "Male" && sex_str !== "Female") continue; // Ignores "Total" aggregate
			if (!age_str.includes("10-year bands")) continue; // Explicitly avoids double-counting 15+, 15-64, etc.
			
			if (year < min_year) min_year = year;
			
			let sex_prefix = (sex_str === "Male") ? "m" : "f";
			let mapped_cohorts = [];
			
			// Map ILOSTAT 10-year age bands to WorldPop 5-year working-age cohorts (Excludes 00, 01, 05, 10)
			if (age_str.includes("15-24")) mapped_cohorts = ["15", "20"];
			else if (age_str.includes("25-34")) mapped_cohorts = ["25", "30"];
			else if (age_str.includes("35-44")) mapped_cohorts = ["35", "40"];
			else if (age_str.includes("45-54")) mapped_cohorts = ["45", "50"];
			else if (age_str.includes("55-64")) mapped_cohorts = ["55", "60"];
			else if (age_str.includes("65+")) mapped_cohorts = ["65", "70", "75", "80"];
			
			if (mapped_cohorts.length === 0) continue;
			
			if (!return_obj[country]) return_obj[country] = { m: {}, f: {} };
			
			// Populate age/sex brackets
			for (let c = 0; c < mapped_cohorts.length; c++) {
				let cohort_key = mapped_cohorts[c];
				if (!return_obj[country][sex_prefix][cohort_key]) return_obj[country][sex_prefix][cohort_key] = {};
				
				return_obj[country][sex_prefix][cohort_key][year] = value;
			}
		}
		
		return {
			data: return_obj,
			earliest_year: (min_year === Infinity) ? 1990 : min_year // Fallback to 1990 if empty
		};
	}
	
	/**
	 * Generates a per-pixel weighted aggregated LFPR raster for Males and Females respectively.
	 */
	static async B_generateLFPRRasters () {
		if (!fs.existsSync(this.output_masks_folder)) fs.mkdirSync(this.output_masks_folder, { recursive: true });
		
		// 1. Fetch CSV context and clamp timeline
		let parsed_ilo = this.A_getILOLocalObject();
		let raw_ilo_data = parsed_ilo.data;
		
		// Filter HYDE years to only process from the CSV's start year onward (prevents 10000 BC extrapolation)
		let hyde_years = landuse_HYDE.sorted_hyde_years.filter(y => y >= parsed_ilo.earliest_year);
		
		let ilo_geocode_obj = admin_modern.getILOColourcodesObject();
		let geocode_raster = GeoPNG.loadImage(admin_modern.input_geocodes_raster); // 4-channel image
		
		// 2. Interpolate temporal ILO data to exactly map to HYDE years
		let lfpr_data = {};
		Object.iterate(raw_ilo_data, (country, sexes) => {
			lfpr_data[country] = { m: {}, f: {} };
			
			Object.iterate(sexes, (sex, cohorts) => {
				Object.iterate(cohorts, (c_key, series) => {
					// Handle cases where survey data only has 1 point (Spline Extrapolator fails if < 2)
					if (Object.keys(series).length < 2) {
						let single_val = Object.values(series)[0];
						if (!lfpr_data[country][sex][c_key]) lfpr_data[country][sex][c_key] = {};
						
						for (let y = 0; y < hyde_years.length; y++) {
							lfpr_data[country][sex][c_key][hyde_years[y]] = single_val;
						}
					} else {
						let interp_series = Object.cubicSplineInterpolation(series, { years: hyde_years });
						if (!lfpr_data[country][sex][c_key]) lfpr_data[country][sex][c_key] = {};
						
						Object.iterate(interp_series, (h_yr, h_val) => {
							// Lock percentages mathematically between 0% and 100%
							lfpr_data[country][sex][c_key][h_yr] = Math.max(0, Math.min(100, h_val));
						});
					}
				});
			});
		});
		
		// 3. Process aggregation logic per year, per sex
		let working_cohorts = ["15", "20", "25", "30", "35", "40", "45", "50", "55", "60", "65", "70", "75", "80"];
		let sexes = ["m", "f"];
		
		for (let y = 0; y < hyde_years.length; y++) {
			let year = hyde_years[y];
			
			for (let s = 0; s < sexes.length; s++) {
				let sex = sexes[s];
				let output_path = `${this.output_masks_folder}lfpr_${sex}_${year}.png`;
				
				if (fs.existsSync(output_path)) continue;
				
				// Preload all 14 working-age float32 demographic rasters into memory
				let pop_rasters = {};
				for (let c = 0; c < working_cohorts.length; c++) {
					let cohort = working_cohorts[c];
					let pop_raster_path = `${global.age_sex.output_rasters}${sex}_${cohort}_${year}.png`;
					if (fs.existsSync(pop_raster_path)) {
						pop_rasters[cohort] = GeoPNG.loadNumberRasterImage(pop_raster_path, { format: "float32" });
					}
				}
				
				// If no demographic rasters were found, skip 
				if (Object.keys(pop_rasters).length === 0) continue;
				let base_raster = pop_rasters[Object.keys(pop_rasters)[0]];
				
				GeoPNG.saveNumberRasterImage({
					file_path: output_path,
					format: "float32",
					width: base_raster.width,
					height: base_raster.height,
					function: (local_index) => {
						let total_working_pop = 0;
						let local_pops = {};
						
						// Fetch localized demographics strictly for this pixel
						for (let c = 0; c < working_cohorts.length; c++) {
							let cohort = working_cohorts[c];
							let c_pop = pop_rasters[cohort] ? pop_rasters[cohort].data[local_index] : 0;
							
							if (c_pop > 0) {
								local_pops[cohort] = c_pop;
								total_working_pop += c_pop;
							}
						}
						
						// Guard Clause: Discards Oceans / Uninhabited Pixels entirely
						if (total_working_pop <= 0) return 0;
						
						let byte_index = local_index * 4;
						
						// Build string precisely matching the dictionary format ("R,G,B")
						let colour_key = [
							geocode_raster.data[byte_index],
							geocode_raster.data[byte_index + 1],
							geocode_raster.data[byte_index + 2]
						].join(",");
						
						let valid_labels = ilo_geocode_obj[colour_key];
						
						if (valid_labels) {
							// Iterate through precedence (Primary nation -> regional fallbacks)
							for (let x = 0; x < valid_labels.length; x++) {
								let country = valid_labels[x];
								let c_data = lfpr_data[country]?.[sex];
								
								if (c_data) {
									let total_labor_force = 0;
									let valid_working_pop = 0;
									
									// Convert cohort populations dynamically into active workforce totals
									for (let c = 0; c < working_cohorts.length; c++) {
										let cohort = working_cohorts[c];
										let c_pop = local_pops[cohort];
										
										if (c_pop > 0) {
											let rate = c_data[cohort]?.[year];
											if (rate !== undefined) {
												total_labor_force += c_pop * (rate / 100);
												valid_working_pop += c_pop;
											}
										}
									}
									
									// If missing data prevents total cohort summing, return localized mean %
									if (valid_working_pop > 0) {
										return (total_labor_force / valid_working_pop) * 100;
									}
								}
							}
						}
						
						// Return 0 if geopolitical boundaries lacked any data intersections
						return 0;
					}
				});
				
				console.log(`- Saved demographically-weighted LFPR mask: ${output_path}`);
				await Blacktraffic.yield();
			}
		}
	}
	
	static async processRasters (arg0_options) {
		let options = (arg0_options) ? arg0_options : {};
		if (!options.exclude) options.exclude = [];
		
		if (!options.exclude.includes("B")) await this.B_generateLFPRRasters();
	}
};