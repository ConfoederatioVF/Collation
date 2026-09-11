global.LFPR_Olivetti = class {
	static input_sex_csv = `${h1}/LFPR_Olivetti/lfpr_sex_olivetti.csv`;
	static intermediate_rasters_folder = `${h1}/LFPR_Olivetti/masks/`;
	static ilo_masks_folder = `${h1}/LFPR_ILO/masks/`; // Fixes the undefined reference/load-order crash
	
	/**
	 * Parses the Olivetti LFPR CSV file, extracting historical
	 * male/female LFPR series per ISO3 code (ranges 0 to 1).
	 */
	static A_getOlivettiLocalObject () {
		let csv_array = File.loadCSVAsArray(this.input_sex_csv, { delimiter: "," });
		let return_obj = {};
		let min_year = Infinity;
		
		if (csv_array.length === 0) return { data: return_obj, earliest_year: 1890 };
		
		// 1. Map headers directly from the cleanly parsed object keys
		let headers = Object.keys(csv_array[0]);
		let year_columns = [];
		
		for (let i = 0; i < headers.length; i++) {
			let yr = parseInt(headers[i]);
			if (!isNaN(yr) && yr >= 1000) {
				year_columns.push(yr);
				if (yr < min_year) min_year = yr;
			}
		}
		
		// 2. Parse data rows cleanly
		for (let i = 0; i < csv_array.length; i++) {
			let row = csv_array[i];
			
			let iso3 = (row["ISO3"] || "").toString().trim();
			let gender_str = (row["Gender"] || "").toString().trim();
			
			if (!iso3) continue;
			
			let sex_prefix = null;
			if (gender_str === "Male") sex_prefix = "m";
			else if (gender_str === "Female") sex_prefix = "f";
			
			if (!sex_prefix) continue;
			
			if (!return_obj[iso3]) return_obj[iso3] = { m: {}, f: {} };
			
			// Extract valid data strictly from the known year columns
			for (let j = 0; j < year_columns.length; j++) {
				let year = year_columns[j];
				let val = row[year.toString()];
				
				if (val !== null && val !== undefined && val !== "") {
					let rate = parseFloat(val);
					if (!isNaN(rate)) {
						// Overwrites safely if multiple sources (e.g. A.1 and A.2) exist for the same country/year
						return_obj[iso3][sex_prefix][year] = rate;
					}
				}
			}
		}
		
		return {
			data: return_obj,
			earliest_year: (min_year === Infinity) ? 1890 : min_year
		};
	}
	
	/**
	 * Generates squashed demographically-weighted rasters.
	 * Uses ILOStat data (normalized to 0-1) where available at the pixel level,
	 * and falls back to strictly in-domain Olivetti historical data.
	 */
	static async B_generateOlivettiRasters () {
		if (!fs.existsSync(this.intermediate_rasters_folder)) fs.mkdirSync(this.intermediate_rasters_folder, { recursive: true });
		
		let parsed_olivetti = this.A_getOlivettiLocalObject();
		let raw_olivetti_data = parsed_olivetti.data;
		
		// Filter HYDE years strictly from the CSV's starting bound onward
		let hyde_years = landuse_HYDE.sorted_hyde_years.filter(y => y >= parsed_olivetti.earliest_year);
		
		// Map raster colors to ISO3
		let geocode_obj = (typeof admin_modern.getISO3ColourcodesObject === "function")
			? admin_modern.getISO3ColourcodesObject()
			: admin_modern.getILOColourcodesObject();
		
		// Pre-load geocodes raster since we'll need it for Olivetti fallbacks across all years
		let geocode_raster = GeoPNG.loadImage(admin_modern.input_geocodes_raster);
		
		// Safe, STRICT In-Domain Interpolation
		let lfpr_data = {};
		Object.iterate(raw_olivetti_data, (iso3, sexes) => {
			lfpr_data[iso3] = { m: {}, f: {} };
			
			Object.iterate(sexes, (sex, series) => {
				let available_years = Object.keys(series).map(Number).sort((a, b) => a - b);
				if (available_years.length === 0) return;
				
				let series_min = available_years[0];
				let series_max = available_years[available_years.length - 1];
				
				if (available_years.length < 2) {
					// Single data point: Only map it if it perfectly matches a HYDE year
					if (hyde_years.includes(series_min)) {
						lfpr_data[iso3][sex][series_min] = series[series_min];
					}
				} else {
					let interp_series = Object.cubicSplineInterpolation(series, { years: hyde_years });
					
					Object.iterate(interp_series, (h_yr_str, h_val) => {
						let h_yr = parseInt(h_yr_str);
						
						// STRICT IN-DOMAIN CLAMP: Disables backwards/forwards flatlining.
						// If a year is out of bounds for this specific country, it receives no data.
						if (h_yr >= series_min && h_yr <= series_max) {
							lfpr_data[iso3][sex][h_yr] = Math.max(0, Math.min(1, h_val));
						}
					});
				}
			});
		});
		
		let working_cohorts = ["15", "20", "25", "30", "35", "40", "45", "50", "55", "60", "65", "70", "75", "80"];
		let sexes = ["m", "f"];
		
		for (let y = 0; y < hyde_years.length; y++) {
			let year = hyde_years[y];
			
			for (let s = 0; s < sexes.length; s++) {
				let sex = sexes[s];
				let output_path = `${this.intermediate_rasters_folder}lfpr_${sex}_${year}.png`;
				
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
				
				if (Object.keys(pop_rasters).length === 0) continue;
				let base_raster = pop_rasters[Object.keys(pop_rasters)[0]];
				
				// Load the modern ILO Stat raster using the locally declared safe path
				let ilo_path = `${this.ilo_masks_folder}lfpr_${sex}_${year}.png`;
				let ilo_raster = fs.existsSync(ilo_path) ? GeoPNG.loadNumberRasterImage(ilo_path, { format: "float32" }) : null;
				
				GeoPNG.saveNumberRasterImage({
					file_path: output_path,
					format: "float32",
					width: base_raster.width,
					height: base_raster.height,
					function: (local_index) => {
						let total_working_pop = 0;
						
						// Fetch localized demographics strictly for this pixel
						for (let c = 0; c < working_cohorts.length; c++) {
							let cohort = working_cohorts[c];
							let c_pop = pop_rasters[cohort] ? pop_rasters[cohort].data[local_index] : 0;
							
							if (c_pop > 0) total_working_pop += c_pop;
						}
						
						// Guard Clause: strictly prevents flat country generation over oceans/uninhabited land
						if (total_working_pop <= 0) return 0;
						
						// 1. Primary Priority: ILOStat Data (Translate 0-100 down to 0-1)
						if (ilo_raster) {
							let ilo_val = ilo_raster.data[local_index];
							if (ilo_val > 0) return ilo_val / 100;
						}
						
						// 2. Secondary Fallback: Olivetti Data
						let byte_index = local_index * 4;
						let colour_key = [
							geocode_raster.data[byte_index],
							geocode_raster.data[byte_index + 1],
							geocode_raster.data[byte_index + 2]
						].join(",");
						
						let valid_labels = geocode_obj[colour_key];
						
						if (valid_labels) {
							for (let x = 0; x < valid_labels.length; x++) {
								let iso3 = valid_labels[x];
								let c_data = lfpr_data[iso3]?.[sex];
								
								if (c_data && c_data[year] !== undefined) {
									return c_data[year];
								}
							}
						}
						
						// If no data exists for this specific coordinate & year combo, return 0
						return 0;
					}
				});
				
				console.log(`- Saved merged ILO & Olivetti demographically-weighted LFPR mask: ${output_path}`);
				await Blacktraffic.yield();
			}
		}
	}
	
	static async processRasters (arg0_options) {
		let options = (arg0_options) ? arg0_options : {};
		if (!options.exclude) options.exclude = [];
		
		if (!options.exclude.includes("B")) await this.B_generateOlivettiRasters();
	}
};