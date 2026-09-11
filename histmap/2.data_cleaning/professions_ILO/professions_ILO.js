global.professions_ILO = class {
	static input_csv = `${h1}/professions_ILO/age_sex_professions.csv`;
	static intermediate_rasters_folder = `${h1}/professions_ILO/rasters/`;
	static output_rasters = `${h1}/professions_ILO/output_rasters/`;
	
	// Dynamic structural mapping: 
	// 'aggregates' are overlapping catch-all terms (we take the Math.max of these to avoid double-counting).
	// 'subsets' are mutually exclusive specifics (we sum these together).
	// The final pixel value is Math.max(best_aggregate, sum_of_subsets).
	static professions_map = {
		agriculture: {
			aggregates: [],
			subsets: ['agriculture']
		},
		manufacturing: {
			aggregates: ['industry'],
			subsets: [
				'construction',
				'manufacturing',
				'mining_and_quarrying_electricity_gas_and_water_supply'
			]
		},
		services: {
			aggregates: ['services', 'non_agriculture'],
			subsets: [
				'public_administration_community_social_and_other_services_and_activities',
				'trade_transportation_accommodation_and_food_and_business_and_administrative_services'
			]
		},
		informal_labour: {
			aggregates: [],
			subsets: ['x_not_elsewhere_classified']
		}
	};
	
	static getUniqueProfessions () {
		if (!fs.existsSync(this.intermediate_rasters_folder)) {
			console.warn(`Folder does not exist: ${this.intermediate_rasters_folder}`);
			return [];
		}
		
		let files = fs.readdirSync(this.intermediate_rasters_folder);
		let unique_profs = new Set();
		let filename_regex = /^prof_(.+)_[mft]_\d{4}\.png$/;
		
		for (let i = 0; i < files.length; i++) {
			let match = files[i].match(filename_regex);
			if (match && match[1]) unique_profs.add(match[1]);
		}
		
		let sorted_profs = Array.from(unique_profs).sort();
		console.log(`Found ${sorted_profs.length} Unique Professions.`);
		for (let i = 0; i < sorted_profs.length; i++) console.log(`- ${sorted_profs[i]}`);
		
		return sorted_profs;
	}
	
	static A_getILOLocalObject () {
		let csv_array = File.loadCSVAsArray(this.input_csv, { delimiter: "," });
		let return_obj = {};
		let unique_professions = new Set();
		let min_year = Infinity;
		
		for (let i = 0; i < csv_array.length; i++) {
			let cols = Object.values(csv_array[i]);
			if (cols.length < 8) continue;
			
			let country  = (cols[0] || "").toString().trim();
			let sex_str  = (cols[3] || "").toString().trim();
			let classif1 = (cols[4] || "").toString().trim();
			let classif2 = (cols[5] || "").toString().trim();
			let year     = parseInt(cols[6]);
			let value    = parseFloat(cols[7]);
			
			if (isNaN(year) || isNaN(value)) continue;
			if (!country || !classif1 || !classif2) continue;
			
			if (year < min_year) min_year = year;
			
			let sex_prefix = 't';
			if (sex_str === "Male") sex_prefix = "m";
			else if (sex_str === "Female") sex_prefix = "f";
			else if (sex_str === "Total") sex_prefix = "t";
			else continue;
			
			let area_type = "national";
			if (classif2.toLowerCase().includes("rural")) area_type = "rural";
			else if (classif2.toLowerCase().includes("urban")) area_type = "urban";
			
			let prof_raw = classif1;
			if (prof_raw.includes(": ")) prof_raw = prof_raw.split(": ")[1];
			
			let prof_clean = prof_raw.replace(/[^a-zA-Z0-9]/g, "_").replace(/_+/g, "_").replace(/^_|_$/g, "").toLowerCase();
			
			if (!return_obj[country]) return_obj[country] = { m: {}, f: {}, t: {} };
			if (!return_obj[country][sex_prefix][area_type]) return_obj[country][sex_prefix][area_type] = {};
			if (!return_obj[country][sex_prefix][area_type][year]) return_obj[country][sex_prefix][area_type][year] = {};
			
			return_obj[country][sex_prefix][area_type][year][prof_clean] = value;
			unique_professions.add(prof_clean);
		}
		
		let shares_obj = {};
		Object.iterate(return_obj, (country, sexes) => {
			shares_obj[country] = { m: {}, f: {}, t: {} };
			Object.iterate(sexes, (sex, areas) => {
				Object.iterate(areas, (area, years) => {
					Object.iterate(years, (year_str, profs) => {
						let yr = parseInt(year_str);
						let total_employed = profs["total"];
						
						if (total_employed && total_employed > 0) {
							Object.iterate(profs, (p_clean, p_val) => {
								if (p_clean === "total") return;
								if (!shares_obj[country][sex][p_clean]) shares_obj[country][sex][p_clean] = { rural: {}, urban: {}, national: {} };
								shares_obj[country][sex][p_clean][area][yr] = Math.max(0, Math.min(1, p_val / total_employed));
							});
						}
					});
				});
			});
		});
		
		unique_professions.delete("total");
		
		return {
			data: shares_obj,
			unique_professions: Array.from(unique_professions),
			earliest_year: (min_year === Infinity) ? 1990 : min_year
		};
	}
	
	static async B_generateProfessionsRasters () {
		if (!fs.existsSync(this.intermediate_rasters_folder)) fs.mkdirSync(this.intermediate_rasters_folder, { recursive: true });
		
		let parsed_ilo = this.A_getILOLocalObject();
		let raw_shares_data = parsed_ilo.data;
		let profs_list = parsed_ilo.unique_professions;
		
		let hyde_years = landuse_HYDE.sorted_hyde_years.filter(y => y >= parsed_ilo.earliest_year);
		let ilo_geocode_obj = admin_modern.getILOColourcodesObject();
		let geocode_raster = GeoPNG.loadImage(admin_modern.input_geocodes_raster);
		
		let interpolated_data = {};
		Object.iterate(raw_shares_data, (country, sexes) => {
			interpolated_data[country] = { m: {}, f: {}, t: {} };
			Object.iterate(sexes, (sex, profs) => {
				Object.iterate(profs, (prof, areas) => {
					if (!interpolated_data[country][sex][prof]) interpolated_data[country][sex][prof] = { rural: {}, urban: {}, national: {} };
					Object.iterate(areas, (area_type, series) => {
						if (Object.keys(series).length === 0) return;
						if (Object.keys(series).length < 2) {
							let single_val = Object.values(series)[0];
							for (let y = 0; y < hyde_years.length; y++) interpolated_data[country][sex][prof][area_type][hyde_years[y]] = single_val;
						} else {
							let interp_series = Object.cubicSplineInterpolation(series, { years: hyde_years });
							Object.iterate(interp_series, (h_yr, h_val) => interpolated_data[country][sex][prof][area_type][h_yr] = Math.max(0, Math.min(1, h_val)));
						}
					});
				});
			});
		});
		
		let working_cohorts = ["15", "20", "25", "30", "35", "40", "45", "50", "55", "60", "65", "70", "75", "80"];
		let sexes = ["m", "f", "t"];
		
		for (let y = 0; y < hyde_years.length; y++) {
			let year = hyde_years[y];
			let rurc_path = `${population_Stadester_Legacy.input_rurc_folder}/stadester_rural_${year}.png`;
			let urbc_path = `${population_Stadester_Legacy.input_urbc_folder}/stadester_urban_${year}.png`;
			if (!fs.existsSync(rurc_path) || !fs.existsSync(urbc_path)) continue;
			
			let rurc_raster = GeoPNG.loadNumberRasterImage(rurc_path, { format: "int32" });
			let urbc_raster = GeoPNG.loadNumberRasterImage(urbc_path, { format: "int32" });
			
			let pop_rasters_m = {}, pop_rasters_f = {};
			for (let c = 0; c < working_cohorts.length; c++) {
				let cohort = working_cohorts[c];
				let m_path = `${global.age_sex.output_rasters}m_${cohort}_${year}.png`;
				let f_path = `${global.age_sex.output_rasters}f_${cohort}_${year}.png`;
				if (fs.existsSync(m_path)) pop_rasters_m[cohort] = GeoPNG.loadNumberRasterImage(m_path, { format: "float32" });
				if (fs.existsSync(f_path)) pop_rasters_f[cohort] = GeoPNG.loadNumberRasterImage(f_path, { format: "float32" });
			}
			
			let lfpr_m_path = `${global.LFPR_Olivetti.intermediate_rasters_folder}lfpr_m_${year}.png`;
			let lfpr_f_path = `${global.LFPR_Olivetti.intermediate_rasters_folder}lfpr_f_${year}.png`;
			let lfpr_raster_m = fs.existsSync(lfpr_m_path) ? GeoPNG.loadNumberRasterImage(lfpr_m_path, { format: "float32" }) : null;
			let lfpr_raster_f = fs.existsSync(lfpr_f_path) ? GeoPNG.loadNumberRasterImage(lfpr_f_path, { format: "float32" }) : null;
			
			for (let s = 0; s < sexes.length; s++) {
				let sex = sexes[s];
				for (let p = 0; p < profs_list.length; p++) {
					let prof = profs_list[p];
					let output_path = `${this.intermediate_rasters_folder}prof_${prof}_${sex}_${year}.png`;
					if (fs.existsSync(output_path)) continue;
					
					let has_data = false;
					for (let c in interpolated_data) {
						let c_target = interpolated_data[c][sex][prof];
						if (c_target && (Object.keys(c_target.national).length > 0 || Object.keys(c_target.rural).length > 0 || Object.keys(c_target.urban).length > 0)) { has_data = true; break; }
					}
					if (!has_data) continue;
					
					GeoPNG.saveNumberRasterImage({
						file_path: output_path,
						format: "float32",
						width: geocode_raster.width,
						height: geocode_raster.height,
						function: (local_index) => {
							let r_pop = rurc_raster.data[local_index] || 0;
							let u_pop = urbc_raster.data[local_index] || 0;
							let total_density = r_pop + u_pop;
							if (total_density <= 0) return 0;
							
							let work_m = 0, work_f = 0;
							for (let c = 0; c < working_cohorts.length; c++) {
								let cohort = working_cohorts[c];
								if (pop_rasters_m[cohort]) work_m += pop_rasters_m[cohort].data[local_index] || 0;
								if (pop_rasters_f[cohort]) work_f += pop_rasters_f[cohort].data[local_index] || 0;
							}
							
							let lfpr_m_val = lfpr_raster_m ? lfpr_raster_m.data[local_index] : 0;
							let lfpr_f_val = lfpr_raster_f ? lfpr_raster_f.data[local_index] : 0;
							let employed_m = work_m * lfpr_m_val;
							let employed_f = work_f * lfpr_f_val;
							
							let target_working = 0, target_employed = 0;
							if (sex === "m") { target_working = work_m; target_employed = employed_m; }
							else if (sex === "f") { target_working = work_f; target_employed = employed_f; }
							else if (sex === "t") { target_working = work_m + work_f; target_employed = employed_m + employed_f; }
							
							if (target_working <= 0 || target_employed <= 0) return 0;
							
							let local_lfpr = target_employed / target_working;
							let r_ratio = r_pop / total_density;
							let u_ratio = u_pop / total_density;
							
							let byte_index = local_index * 4;
							let colour_key = [geocode_raster.data[byte_index], geocode_raster.data[byte_index + 1], geocode_raster.data[byte_index + 2]].join(",");
							let valid_labels = ilo_geocode_obj[colour_key];
							
							if (valid_labels) {
								for (let x = 0; x < valid_labels.length; x++) {
									let country = valid_labels[x];
									let c_data = interpolated_data[country]?.[sex]?.[prof];
									
									if (c_data) {
										let r_share = c_data.rural[year], u_share = c_data.urban[year], n_share = c_data.national[year];
										let actual_r_share = r_share !== undefined ? r_share : (n_share !== undefined ? n_share : 0);
										let actual_u_share = u_share !== undefined ? u_share : (n_share !== undefined ? n_share : 0);
										
										if (actual_r_share === 0 && actual_u_share === 0 && r_share === undefined && u_share === undefined && n_share === undefined) continue;
										
										let sector_share_of_employed = (actual_r_share * r_ratio) + (actual_u_share * u_ratio);
										return sector_share_of_employed * local_lfpr;
									}
								}
							}
							return 0;
						}
					});
					console.log(`- Saved demographically-isolated Profession mask: ${output_path}`);
					await Blacktraffic.yield();
				}
			}
		}
	}
	
	/**
	 * Takes the intermediate specific professions and bins them into structural categories dynamically,
	 * using the mappings and double-counting protection logic defined in professions_map.
	 */
	static async C_binProfessionsRasters () {
		if (!fs.existsSync(this.output_rasters)) fs.mkdirSync(this.output_rasters, { recursive: true });
		
		let parsed_ilo = this.A_getILOLocalObject();
		let hyde_years = landuse_HYDE.sorted_hyde_years.filter(y => y >= parsed_ilo.earliest_year);
		
		let sexes = ["m", "f", "t"];
		let target_bins = Object.keys(this.professions_map);
		
		for (let y = 0; y < hyde_years.length; y++) {
			let year = hyde_years[y];
			
			for (let s = 0; s < sexes.length; s++) {
				let sex = sexes[s];
				
				for (let b = 0; b < target_bins.length; b++) {
					let bin = target_bins[b];
					let mapping = this.professions_map[bin];
					let output_path = `${this.output_rasters}${bin}_${sex}_${year}.png`;
					
					if (fs.existsSync(output_path)) continue;
					
					let loaded_rasters = {};
					let all_keys = [...mapping.aggregates, ...mapping.subsets];
					let has_any_raster = false;
					
					// Load available intermediate rasters dynamically
					for (let k = 0; k < all_keys.length; k++) {
						let prof_key = all_keys[k];
						let inter_path = `${this.intermediate_rasters_folder}prof_${prof_key}_${sex}_${year}.png`;
						
						if (fs.existsSync(inter_path)) {
							loaded_rasters[prof_key] = GeoPNG.loadNumberRasterImage(inter_path, { format: "float32" });
							has_any_raster = true;
						}
					}
					
					if (!has_any_raster) continue;
					
					let base_raster = loaded_rasters[Object.keys(loaded_rasters)[0]];
					
					GeoPNG.saveNumberRasterImage({
						file_path: output_path,
						format: "float32",
						width: base_raster.width,
						height: base_raster.height,
						function: (local_index) => {
							// 1. Evaluate Max of Aggregates (e.g. overlapping definitions like 'services' vs 'non_agriculture')
							let agg_max = 0;
							for (let a = 0; a < mapping.aggregates.length; a++) {
								let agg_key = mapping.aggregates[a];
								if (loaded_rasters[agg_key]) {
									agg_max = Math.max(agg_max, loaded_rasters[agg_key].data[local_index] || 0);
								}
							}
							
							// 2. Sum of Subsets (mutually exclusive segments)
							let sub_sum = 0;
							for (let s_idx = 0; s_idx < mapping.subsets.length; s_idx++) {
								let sub_key = mapping.subsets[s_idx];
								if (loaded_rasters[sub_key]) {
									sub_sum += loaded_rasters[sub_key].data[local_index] || 0;
								}
							}
							
							// 3. Final Protection: Takes whichever is larger (meaning we don't accidentally add manufacturing subsets ON TOP of the entire industry aggregate)
							let final_val = Math.max(agg_max, sub_sum);
							
							// Hard clamp to 1.0 (100% of the demographic workforce capacity)
							return Math.min(1.0, final_val);
						}
					});
					
					console.log(`- Saved dynamically structured bin mask: ${output_path}`);
					await Blacktraffic.yield();
				}
			}
		}
	}
	
	static async processRasters (arg0_options) {
		let options = (arg0_options) ? arg0_options : {};
		if (!options.exclude) options.exclude = [];
		
		if (!options.exclude.includes("B")) await this.B_generateProfessionsRasters();
		if (!options.exclude.includes("C")) await this.C_binProfessionsRasters();
	}
};