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
	
	static async B_generateWIDRasters () {
		//Declare local instance variables
		let iso2_obj = admin_modern.getWIDColourcodesObject();
		let iso2_raster = GeoPNG.loadImage(admin_modern.input_iso2_geocodes_raster);
		let options = this.options;
		let years = landuse_HYDE.sorted_hyde_years;
		
		//Create folders
		for (let i = 0; i < options.variables.length; i++) {
			let local_folder_path = `${this.bf}${options.variables[i]}/`;
			let local_json_obj = JSON.parse(fs.readFileSync(`${this.input_json}${options.variables[i]}.json`,  "utf8"));
			
			if (!fs.existsSync(local_folder_path))
				fs.mkdirSync(local_folder_path, { recursive: true });
			
			//local_json_obj needs to be processed for years
			Object.iterate(local_json_obj, (local_key, local_value) => 
				Object.cubicSplineInterpolation(local_value, { years }));
			
			//Filter years with data
			let years_with_data = [];
			for (let x = 0; x < years.length; x++) {
				let year = years[x];
				let has_data = false;
				Object.iterate(local_json_obj, (local_key, local_value) => {
					if (local_value[year]) has_data = true;
				});
				if (has_data) years_with_data.push(year);
			}
			
			await GeoPNG.processTimeseriesParallel({
				items: years_with_data,
				concurrency: 4,
				name: `wealth_income_WID B_generateWIDRasters (${options.variables[i]})`,
				handler: async (year) => {
					let local_output_file_path = `${local_folder_path}${options.variables[i]}_${year}.png`;
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
	
	static async processRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		if (!options.exclude) options.exclude = [];
		
		//Process WID
		if (!options.exclude.includes("A")) await this.A_cacheWIDObjects();
		if (!options.exclude.includes("B")) await this.B_generateWIDRasters();
	}
};