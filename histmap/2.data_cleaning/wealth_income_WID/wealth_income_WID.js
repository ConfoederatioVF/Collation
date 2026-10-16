global.wealth_income_WID = class {
	static bf = `${h2}/wealth_income_WID/`;
	static input_folder = `${h1}/wealth_income_WID/`;
	static input_json = `${this.input_folder}json/`;
	static intermediate_discretionary_income = `${this.bf}discretionary_income/`;
	static intermediate_disposable_income = `${this.bf}disposable_income/`;
	static intermediate_net_income = `${this.bf}net_income/`;
	static intermediate_net_wealth = `${this.bf}net_wealth/`;
	
	static options = {
		//Metadata
		deflator: (174.6/326.031)*0.9004, //(CPI_$2000/CPI_$2025)*EUR_USD_2000
		file_prefix: "WID_data_",
		file_suffix: ".csv",
		variables: ["disposable_income", "net_income", "discretionary_income", "net_wealth"],
		
		//Priority suffixes: Equal-split adults (j996) is the gold standard, followed by individual adults (j992)
		priority_suffixes: ["j996", "i996", "j992", "i992", "j999", "i999"],
		
		//Income
		net_income: ["aptinc"],
		disposable_income: ["aconhn", "asavhn"], //Cash Disposable Income = Household Consumption + Household Saving
		discretionary_income: ["asavho", "aindgo"], //Savings Rate + Social Transfers
		
		//Wealth
		net_wealth: ["ahweal"],
		
		//Currency Conversion (Market Exchange Rate: Local Currency per EUR)
		exchange_rate: ["xlceuxi", "alceuxi"]
	};
	
	static async getWIDObject (arg0_key) {
		let key = arg0_key;
		let all_files = await File.getAllFiles(this.input_folder);
		let prefix_array = this.options[key];
		let return_obj = {};
		let exchange_rates = this.options.exchange_rate;
		
		for (let i = 0; i < all_files.length; i++) {
			let basename = path.basename(all_files[i]);
			
			if (basename.startsWith(this.options.file_prefix) && basename.endsWith(this.options.file_suffix)) {
				let csv_array = File.loadCSVAsArray(all_files[i], { delimiter: ";" });
				let iso_code = basename.replace(this.options.file_prefix, "").replace(this.options.file_suffix, "");
				
				if (!return_obj[iso_code]) return_obj[iso_code] = {};
				let local_obj = return_obj[iso_code];
				
				for (let x = 0; x < csv_array.length; x++) {
					let csv_row = csv_array[x];
					let v = csv_row.variable;
					
					// 1. Capture Macroeconomic Exchange Rates
					for (let e = 0; e < exchange_rates.length; e++) {
						if (v.startsWith(exchange_rates[e])) {
							if (!local_obj[csv_row.year]) local_obj[csv_row.year] = {};
							local_obj[csv_row.year].exchange_rate = parseFloat(csv_row.value);
							break;
						}
					}
					
					// 2. Capture Target Variables
					for (let y = 0; y < prefix_array.length; y++) {
						let current_prefix = prefix_array[y];
						
						if (v.startsWith(current_prefix)) {
							if (csv_row.percentile === "p0p100") {
								if (!local_obj[csv_row.year]) local_obj[csv_row.year] = {};
								if (!local_obj[csv_row.year][current_prefix]) local_obj[csv_row.year][current_prefix] = {};
								
								let suffix = v.replace(current_prefix, "");
								local_obj[csv_row.year][current_prefix][suffix] = parseFloat(csv_row.value);
							}
						}
					}
				}
			}
			console.log(`- Finished scanning ${i + 1}/${all_files.length} .csv files ...`);
			await Blacktraffic.yield();
		}
		
		// Post-processing: Resolve priorities, convert currency, and sum components
		let iso_codes = Object.keys(return_obj);
		for (let i = 0; i < iso_codes.length; i++) {
			let current_iso = iso_codes[i];
			let year_data = return_obj[current_iso];
			let flattened_year_map = {};
			
			// WID variables are in Constant Base-Year Currency. 
			// We must find the most recent year's exchange rate to act as our Base Rate.
			let base_exchange_rate = 1;
			let available_years = Object.keys(year_data).map(Number).sort((a, b) => b - a); // Descending order
			
			for (let yr of available_years) {
				if (year_data[yr] && year_data[yr].exchange_rate) {
					base_exchange_rate = year_data[yr].exchange_rate;
					break;
				}
			}
			
			for (let current_year in year_data) {
				let data = year_data[current_year];
				let year_sum = 0;
				let valid_year = false;
				
				for (let pref of prefix_array) {
					if (data[pref]) {
						// Pick the highest-priority demographic suffix available
						let best_suffix = this.options.priority_suffixes.find(s => data[pref][s] !== undefined);
						
						if (best_suffix) {
							let raw_value = data[pref][best_suffix];
							
							// Transform: (Base LCU / Base LCU per EUR) * Universal Deflator
							year_sum += (raw_value / base_exchange_rate) * this.options.deflator;
							valid_year = true;
						}
					}
				}
				
				if (valid_year) flattened_year_map[current_year] = year_sum;
			}
			return_obj[current_iso] = flattened_year_map;
		}
		
		return return_obj;
	}
	
	static async A_cacheWIDObjects () {
		let options = this.options;
		
		if (!fs.existsSync(this.input_json)) fs.mkdirSync(this.input_json, { recursive: true });
		
		for (let i = 0; i < options.variables.length; i++) {
			let var_name = options.variables[i];
			let output_file_path = `${this.input_json}${var_name}.json`;
			
			console.log(`Processing ${var_name}...`);
			let variable_obj = await this.getWIDObject(var_name);
			
			fs.writeFileSync(output_file_path, JSON.stringify(variable_obj, null, 2));
			console.log(`Saved cache file to ${output_file_path}.`);
		}
	}
	
	/**
	 * Reconciles national accounts WID series by dasymetrically subtracting resolved subsets from regional
	 * aggregates and applying anchor-year relativistic backcalculation via GDP PPP per capita.
	 * 
	 * @param {Object} [arg0_options]
	 *  @param {Array<string>} [arg0_options.variables] - Target variables to reconcile.
	 */
	static async B_reconcileRegionalFallbacks (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		if (!options.variables) options.variables = this.options.variables;
		
		//Declare local instance variables
		let dev_index_file = path.join(
			(typeof root_dir !== "undefined") ? root_dir : ".",
			"histmap/2.data_cleaning/population_Stadester/stadester_national_populations.json"
		);
		let geocodes_lines = fs.readFileSync(admin_modern.input_iso2_geocodes_csv, "utf8").trim().split("\n").slice(1);
		let hyde_years = landuse_HYDE.sorted_hyde_years;
		let iso2_to_iso3 = {};
		let national_populations = JSON.parse(fs.readFileSync(dev_index_file, "utf8"));
		let regional_csv = File.loadCSVAsJSON(admin_modern.input_regional_geocodes_csv, { delimiter: ";", mode: "vertical" });
		let regions = {};
		let sovereign_map = {
			"CN": "CHN", "DE": "DEU", "DK": "DNK", "FR": "FRA", "GB": "GBR",
			"LT": "LTU", "MA": "MAR", "NL": "NLD", "PL": "POL", "RU": "RUS",
			"TZ": "TZA", "US": "USA"
		};
		
		//Destructure iso2_geocodes
		for (let i = 0; i < geocodes_lines.length; i++) {
			let line = geocodes_lines[i];
			let parts = line.split(";");
			if (parts[0] && parts[1]) iso2_to_iso3[parts[0].trim()] = parts[1].trim();
		}
		
		//Destructure regional aggregates
		for (let r_key in regional_csv) {
			let str = regional_csv[r_key]["Other Geocodes"]?.[0];
			if (str) regions[r_key] = str.split(",").map(s => s.trim()).filter(Boolean);
		}
		
		let gdp_ppp_extensive = GDP_PPP.getGDP_PPPObject();
		
		let getPop = (iso2, yr) => {
			let iso3 = iso2_to_iso3[iso2];
			if (!iso3) return 0;
			if (Object.values(sovereign_map).includes(iso3))
				if (sovereign_map[iso2] !== iso3) return 0;
			return national_populations[yr]?.[iso3] || 0;
		};
		
		let getGdpPc = (iso2, yr) => {
			let iso3 = iso2_to_iso3[iso2];
			if (!iso3) return 0;
			let p = getPop(iso2, yr);
			if (p === 0) return 0;
			return (gdp_ppp_extensive[iso3]?.[yr] || 0) / p;
		};
		
		for (let i = 0; i < options.variables.length; i++) {
			let var_name = options.variables[i];
			let file_path = `${this.input_json}${var_name}.json`;
			if (!fs.existsSync(file_path)) continue;
			
			console.log(`Reconciling regional fallbacks for ${var_name}...`);
			let var_data = JSON.parse(fs.readFileSync(file_path, "utf8"));
			let countries = Object.keys(var_data).filter(k => k.length === 2 && !k.includes("-"));
			
			//1. Anchor-year identification & relativistic backcalculation for countries with empirical observations
			for (let x = 0; x < countries.length; x++) {
				let c = countries[x];
				let series = var_data[c] || {};
				let emp_years = Object.keys(series).map(Number).sort((a, b) => a - b);
				
				if (emp_years.length > 0) {
					let t_anchor = emp_years[0];
					let val_anchor = series[t_anchor];
					let gdp_pc_anchor = getGdpPc(c, t_anchor);
					
					if (val_anchor > 0 && gdp_pc_anchor > 0) {
						for (let y = 0; y < hyde_years.length; y++) {
							let yr = hyde_years[y];
							if (yr < t_anchor) {
								let g_yr = getGdpPc(c, yr);
								if (g_yr > 0) series[yr] = val_anchor * (g_yr / gdp_pc_anchor);
							}
						}
					}
					
					let t_latest = emp_years[emp_years.length - 1];
					let val_latest = series[t_latest];
					let gdp_pc_latest = getGdpPc(c, t_latest);
					
					if (val_latest > 0 && gdp_pc_latest > 0) {
						for (let y = 0; y < hyde_years.length; y++) {
							let yr = hyde_years[y];
							if (yr > t_latest) {
								let g_yr = getGdpPc(c, yr);
								if (g_yr > 0) series[yr] = val_latest * (g_yr / gdp_pc_latest);
							}
						}
					}
				}
			}
			
			//2. Regional dasymetric reconciliation & residual re-balancing
			for (let r_key in regions) {
				let members = regions[r_key];
				let reg_series = var_data[r_key] || var_data[r_key.replace("-MER", "").replace("-PPP", "")];
				if (!reg_series) continue;
				
				for (let y = 0; y < hyde_years.length; y++) {
					let yr = hyde_years[y];
					let i_R = reg_series[yr];
					if (i_R === undefined || i_R === null) continue;
					
					let P_R = 0;
					let reg_gdp_ppp = 0;
					let S = [];
					let U = [];
					
					for (let z = 0; z < members.length; z++) {
						let m = members[z];
						let p = getPop(m, yr);
						let g = getGdpPc(m, yr)*p;
						P_R += p;
						reg_gdp_ppp += g;
						
						if (var_data[m]?.[yr] !== undefined) S.push(m);
						else U.push(m);
					}
					
					let g_R = (P_R > 0) ? (reg_gdp_ppp / P_R) : 0;
					
					//Fill completely missing members from regional indicator scaled to country relative productivity
					for (let z = 0; z < U.length; z++) {
						let u = U[z];
						if (!var_data[u]) var_data[u] = {};
						let g_u = getGdpPc(u, yr);
						if (g_u > 0 && g_R > 0) var_data[u][yr] = i_R * (g_u / g_R);
					}
					
					//Dasymetric residual re-balancing if residual pool is positive
					let V_R = i_R * P_R;
					let V_S = 0;
					for (let z = 0; z < S.length; z++) V_S += var_data[S[z]][yr] * getPop(S[z], yr);
					let V_res = V_R - V_S;
					
					if (V_res > 0 && U.length > 0) {
						let hat_V_U = 0;
						for (let z = 0; z < U.length; z++) hat_V_U += (var_data[U[z]][yr] || 0) * getPop(U[z], yr);
						if (hat_V_U > 0) {
							let lambda = Math.min(Math.max(V_res / hat_V_U, 0.25), 4.0);
							for (let z = 0; z < U.length; z++) var_data[U[z]][yr] *= lambda;
						}
					}
				}
			}
			
			fs.writeFileSync(file_path, JSON.stringify(var_data, null, 2));
			console.log(`Saved reconciled dataset to ${file_path}.`);
		}
	}
	
	/**
	 * Generates WID raster surfaces for the specified variables and years.
	 * 
	 * @param {Object} [arg0_options]
	 *  @param {number} [arg0_options.concurrency=4]
	 *  @param {boolean} [arg0_options.overwrite=true]
	 *  @param {Array<string>} [arg0_options.variables]
	 *  @param {Array<number>} [arg0_options.years]
	 */
	static async C_generateWIDRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		if (!options.concurrency) options.concurrency = 4;
		if (options.overwrite === undefined) options.overwrite = true;
		if (!options.variables) options.variables = this.options.variables;
		
		//Declare local instance variables
		let all_hyde_years = landuse_HYDE.sorted_hyde_years;
		let iso2_obj = admin_modern.getWIDColourcodesObject();
		let iso2_raster = GeoPNG.loadImage(admin_modern.input_iso2_geocodes_raster);
		let target_variables = options.variables;
		let years = (options.years) ? options.years : landuse_HYDE.sorted_hyde_years;
		
		//Create folders
		for (let i = 0; i < target_variables.length; i++) {
			let current_variable = target_variables[i];
			let local_folder_path = `${this.bf}${current_variable}/`;
			let local_json_obj = JSON.parse(fs.readFileSync(`${this.input_json}${current_variable}.json`, "utf8"));
			
			if (!fs.existsSync(local_folder_path))
				fs.mkdirSync(local_folder_path, { recursive: true });
			
			//local_json_obj needs to be processed for all HYDE years via cubic spline
			Object.iterate(local_json_obj, (local_key, local_value) => 
				Object.cubicSplineInterpolation(local_value, { years: all_hyde_years }));
			
			//Filter years with data matching target_years
			let years_with_data = [];
			for (let x = 0; x < years.length; x++) {
				let year = years[x];
				let has_data = false;
				Object.iterate(local_json_obj, (local_key, local_value) => {
					if (local_value[year]) has_data = true;
				});
				if (has_data) years_with_data.push(year);
			}
			
			if (!options.overwrite)
				years_with_data = years_with_data.filter(y => !fs.existsSync(`${local_folder_path}${current_variable}_${y}.png`));
			
			if (years_with_data.length === 0) {
				console.log(`- All rasters up to date for ${current_variable}.`);
				continue;
			}
			
			await GeoPNG.processTimeseriesParallel({
				items: years_with_data,
				concurrency: options.concurrency,
				name: `wealth_income_WID C_generateWIDRasters (${current_variable})`,
				handler: async (year) => {
					let local_output_file_path = `${local_folder_path}${current_variable}_${year}.png`;
					GeoPNG.saveNumberRasterImage({
						file_path: local_output_file_path,
						format: "float32",
						height: 2160,
						width: 4320,
						function: (local_index) => {
							let byte_index = local_index * 4;
							let local_colour_key = [
								iso2_raster.data[byte_index],
								iso2_raster.data[byte_index + 1],
								iso2_raster.data[byte_index + 2]
							].join(",");
							let local_geocodes = iso2_obj[local_colour_key];
							let local_value;
							
							//Iterate over all local_geocodes
							if (local_geocodes)
								for (let y = 0; y < local_geocodes.length; y++)
									if (local_json_obj[local_geocodes[y]]?.[year]) {
										local_value = local_json_obj[local_geocodes[y]][year];
										break;
									}
							
							//Return statement
							return local_value;
						}
					});
					console.log(`- Saved ${local_output_file_path}.`);
				}
			});
		}
	}
	
	static B_generateWIDRasters (arg0_options) {
		return this.C_generateWIDRasters(arg0_options);
	}
	
	static async processRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		if (!options.exclude) options.exclude = [];
		
		//Process WID
		if (!options.exclude.includes("A")) await this.A_cacheWIDObjects(options);
		if (!options.exclude.includes("B")) await this.B_reconcileRegionalFallbacks(options);
		if (!options.exclude.includes("C")) await this.C_generateWIDRasters(options);
	}
};