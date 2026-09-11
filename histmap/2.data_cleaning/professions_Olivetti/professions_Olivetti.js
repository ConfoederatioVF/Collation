global.professions_Olivetti = class {
	static input_csv = `${h1}/professions_Olivetti/professions_sex_Olivetti.csv`;
	static output_rasters = `${h1}/professions_Olivetti/output_rasters/`;
	
	// External raster dependencies
	static ilo_rasters_folder = `${h1}/professions_ILO/output_rasters/`;
	static lfpr_rasters_folder = `${h1}/LFPR_Olivetti/masks/`;
	
	/**
	 * Parses the Olivetti Professions CSV file, extracting historical
	 * Male/Female workforce distributions per ISO3 code.
	 */
	static A_getOlivettiLocalObject () {
		let csv_array = File.loadCSVAsArray(this.input_csv, { delimiter: "," });
		let return_obj = {};
		let min_year = Infinity;
		
		if (csv_array.length === 0) return { data: return_obj, earliest_year: 1890 };
		
		// Map headers to isolate year columns numerically
		let headers = Object.keys(csv_array[0]);
		let year_columns = [];
		
		for (let i = 0; i < headers.length; i++) {
			let yr = parseInt(headers[i]);
			if (!isNaN(yr) && yr >= 1000) {
				year_columns.push(yr);
				if (yr < min_year) min_year = yr;
			}
		}
		
		for (let i = 0; i < csv_array.length; i++) {
			let row = csv_array[i];
			
			let iso3 = (row["ISO3"] || "").toString().trim();
			let gender_str = (row["Gender"] || "").toString().trim();
			let sector_raw = (row["Sector"] || "").toString().trim().toLowerCase();
			
			if (!iso3 || !sector_raw) continue;
			
			let sex_prefix = null;
			if (gender_str === "Male") sex_prefix = "m";
			else if (gender_str === "Female") sex_prefix = "f";
			
			if (!sex_prefix) continue;
			
			// Strictly capture the sectors defined in Olivetti
			let sector_clean = "";
			if (sector_raw.includes("agriculture")) sector_clean = "agriculture";
			else if (sector_raw.includes("manufacturing")) sector_clean = "manufacturing";
			else continue;
			
			if (!return_obj[iso3]) return_obj[iso3] = { m: {}, f: {} };
			if (!return_obj[iso3][sex_prefix][sector_clean]) return_obj[iso3][sex_prefix][sector_clean] = {};
			
			for (let j = 0; j < year_columns.length; j++) {
				let year = year_columns[j];
				let val = row[year.toString()];
				
				if (val !== null && val !== undefined && val !== "") {
					let rate = parseFloat(val);
					if (!isNaN(rate)) {
						return_obj[iso3][sex_prefix][sector_clean][year] = Math.max(0, Math.min(1, rate));
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
	 * Generates final standardised bin rasters. Uses ILO data as the master precedence.
	 * Calculates 'Services' seamlessly as the residual (1 - Ag - Mfg - ILO_Informal).
	 */
	static async B_generateOlivettiRasters () {
		if (!fs.existsSync(this.output_rasters)) fs.mkdirSync(this.output_rasters, { recursive: true });
		
		let parsed_olivetti = this.A_getOlivettiLocalObject();
		let raw_olivetti_data = parsed_olivetti.data;
		
		let hyde_years = landuse_HYDE.sorted_hyde_years.filter(y => y >= parsed_olivetti.earliest_year);
		
		let geocode_obj = (typeof admin_modern.getISO3ColourcodesObject === "function")
			? admin_modern.getISO3ColourcodesObject()
			: admin_modern.getILOColourcodesObject();
		
		let geocode_raster = GeoPNG.loadImage(admin_modern.input_geocodes_raster);
		
		// STRICT In-Domain Interpolation
		let interpolated_data = {};
		Object.iterate(raw_olivetti_data, (iso3, sexes) => {
			interpolated_data[iso3] = { m: {}, f: {} };
			
			Object.iterate(sexes, (sex, sectors) => {
				Object.iterate(sectors, (sector, series) => {
					if (!interpolated_data[iso3][sex][sector]) interpolated_data[iso3][sex][sector] = {};
					
					let available_years = Object.keys(series).map(Number).sort((a, b) => a - b);
					if (available_years.length === 0) return;
					
					let series_min = available_years[0];
					let series_max = available_years[available_years.length - 1];
					
					if (available_years.length < 2) {
						if (hyde_years.includes(series_min)) interpolated_data[iso3][sex][sector][series_min] = series[series_min];
					} else {
						let interp_series = Object.cubicSplineInterpolation(series, { years: hyde_years });
						Object.iterate(interp_series, (h_yr_str, h_val) => {
							let h_yr = parseInt(h_yr_str);
							// Prevents forward/backward flatlining beyond known records
							if (h_yr >= series_min && h_yr <= series_max) {
								interpolated_data[iso3][sex][sector][h_yr] = Math.max(0, Math.min(1, h_val));
							}
						});
					}
				});
			});
		});
		
		let bins = ['agriculture', 'manufacturing', 'services', 'informal_labour'];
		let working_cohorts = ["15", "20", "25", "30", "35", "40", "45", "50", "55", "60", "65", "70", "75", "80"];
		let primary_sexes = ["m", "f"];
		
		for (let y = 0; y < hyde_years.length; y++) {
			let year = hyde_years[y];
			
			// --- STEP 1: Process Male and Female distinct distributions ---
			for (let s = 0; s < primary_sexes.length; s++) {
				let sex = primary_sexes[s];
				
				// Quick Optimization: Skip if all bins for this sex/year are complete
				let all_m_f_exist = true;
				for (let b = 0; b < bins.length; b++) {
					if (!fs.existsSync(`${this.output_rasters}${bins[b]}_${sex}_${year}.png`)) { all_m_f_exist = false; break; }
				}
				if (all_m_f_exist) continue;
				
				// Load local LFPR (Needed to convert Olivetti % Workforce into % Demographics)
				let lfpr_path = `${this.lfpr_rasters_folder}lfpr_${sex}_${year}.png`;
				if (!fs.existsSync(lfpr_path)) continue;
				let lfpr_raster = GeoPNG.loadNumberRasterImage(lfpr_path, { format: "float32" });
				
				// Load ILO Precedence Rasters
				let ilo_rasters = {};
				for (let b = 0; b < bins.length; b++) {
					let p = `${this.ilo_rasters_folder}${bins[b]}_${sex}_${year}.png`;
					if (fs.existsSync(p)) ilo_rasters[bins[b]] = GeoPNG.loadNumberRasterImage(p, { format: "float32" });
				}
				
				for (let b = 0; b < bins.length; b++) {
					let bin = bins[b];
					let output_path = `${this.output_rasters}${bin}_${sex}_${year}.png`;
					if (fs.existsSync(output_path)) continue;
					
					GeoPNG.saveNumberRasterImage({
						file_path: output_path,
						format: "float32",
						width: geocode_raster.width,
						height: geocode_raster.height,
						function: (local_index) => {
							let lfpr_val = lfpr_raster.data[local_index] || 0;
							if (lfpr_val <= 0) return 0; // Skip uninhabited or zero-workforce pixels
							
							let byte_index = local_index * 4;
							let colour_key = [geocode_raster.data[byte_index], geocode_raster.data[byte_index + 1], geocode_raster.data[byte_index + 2]].join(",");
							
							// Check if ILO has defined data for this pixel
							let ilo_ag = ilo_rasters['agriculture'] ? ilo_rasters['agriculture'].data[local_index] : 0;
							let ilo_mfg = ilo_rasters['manufacturing'] ? ilo_rasters['manufacturing'].data[local_index] : 0;
							let ilo_serv = ilo_rasters['services'] ? ilo_rasters['services'].data[local_index] : 0;
							let ilo_inf = ilo_rasters['informal_labour'] ? ilo_rasters['informal_labour'].data[local_index] : 0;
							let total_ilo = ilo_ag + ilo_mfg + ilo_serv + ilo_inf;
							
							// Fetch Olivetti Fallbacks
							let ag_share = 0, mfg_share = 0;
							let has_olivetti = false;
							let valid_labels = geocode_obj[colour_key];
							
							if (valid_labels) {
								for (let x = 0; x < valid_labels.length; x++) {
									let iso3 = valid_labels[x];
									let c_data = interpolated_data[iso3]?.[sex];
									
									if (c_data && (c_data['agriculture']?.[year] !== undefined || c_data['manufacturing']?.[year] !== undefined)) {
										ag_share = c_data['agriculture']?.[year] || 0;
										mfg_share = c_data['manufacturing']?.[year] || 0;
										has_olivetti = true;
										break;
									}
								}
							}
							
							// If absolutely no sources have recorded data, output 0 cleanly
							if (total_ilo === 0 && !has_olivetti) return 0;
							
							// Return correct contextual bin calculations 
							if (bin === 'agriculture') {
								return ilo_ag > 0 ? ilo_ag : (ag_share * lfpr_val);
							}
							else if (bin === 'manufacturing') {
								return ilo_mfg > 0 ? ilo_mfg : (mfg_share * lfpr_val);
							}
							else if (bin === 'informal_labour') {
								return ilo_inf; // Olivetti does not define informal labor, rely solely on ILO
							}
							else if (bin === 'services') {
								if (ilo_serv > 0) return ilo_serv;
								
								// Calculate Residual: Uses ILO where existing, falling back seamlessly to Olivetti
								let final_ag = ilo_ag > 0 ? ilo_ag : (ag_share * lfpr_val);
								let final_mfg = ilo_mfg > 0 ? ilo_mfg : (mfg_share * lfpr_val);
								let final_inf = ilo_inf;
								
								// Services = 100% of Workforce minus Agriculture, Manufacturing, and Informal
								// Math.max prevents fractional errors from breaking negative
								return Math.max(0, lfpr_val - final_ag - final_mfg - final_inf);
							}
							
							return 0;
						}
					});
					console.log(`- Saved merged structural bin mask: ${output_path}`);
					await Blacktraffic.yield();
				}
			}
			
			// --- STEP 2: Demographically Weight the 'Total' (t) Distributions ---
			let pop_rasters_m = {}, pop_rasters_f = {};
			let preloaded_demographics = false;
			
			for (let b = 0; b < bins.length; b++) {
				let bin = bins[b];
				let output_path_t = `${this.output_rasters}${bin}_t_${year}.png`;
				if (fs.existsSync(output_path_t)) continue;
				
				let raster_m_path = `${this.output_rasters}${bin}_m_${year}.png`;
				let raster_f_path = `${this.output_rasters}${bin}_f_${year}.png`;
				if (!fs.existsSync(raster_m_path) || !fs.existsSync(raster_f_path)) continue;
				
				// Lazy load demographics to save heavy parsing times
				if (!preloaded_demographics) {
					for (let c = 0; c < working_cohorts.length; c++) {
						let cohort = working_cohorts[c];
						let m_path = `${global.age_sex.output_rasters}m_${cohort}_${year}.png`;
						let f_path = `${global.age_sex.output_rasters}f_${cohort}_${year}.png`;
						
						if (fs.existsSync(m_path)) pop_rasters_m[cohort] = GeoPNG.loadNumberRasterImage(m_path, { format: "float32" });
						if (fs.existsSync(f_path)) pop_rasters_f[cohort] = GeoPNG.loadNumberRasterImage(f_path, { format: "float32" });
					}
					preloaded_demographics = true;
				}
				
				let raster_m = GeoPNG.loadNumberRasterImage(raster_m_path, { format: "float32" });
				let raster_f = GeoPNG.loadNumberRasterImage(raster_f_path, { format: "float32" });
				
				GeoPNG.saveNumberRasterImage({
					file_path: output_path_t,
					format: "float32",
					width: raster_m.width,
					height: raster_m.height,
					function: (local_index) => {
						let pop_m = 0, pop_f = 0;
						for (let c = 0; c < working_cohorts.length; c++) {
							let cohort = working_cohorts[c];
							if (pop_rasters_m[cohort]) pop_m += pop_rasters_m[cohort].data[local_index] || 0;
							if (pop_rasters_f[cohort]) pop_f += pop_rasters_f[cohort].data[local_index] || 0;
						}
						
						let total_pop = pop_m + pop_f;
						if (total_pop <= 0) return 0;
						
						let val_m = raster_m.data[local_index] || 0;
						let val_f = raster_f.data[local_index] || 0;
						
						return ((val_m * pop_m) + (val_f * pop_f)) / total_pop;
					}
				});
				console.log(`- Saved demographically-weighted Total bin mask: ${output_path_t}`);
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