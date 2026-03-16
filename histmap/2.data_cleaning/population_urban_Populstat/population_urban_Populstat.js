global.population_urban_Populstat = class { //[WIP] - Finish class body
	static bf = `${h1}/population_urban_Populstat/`;
	static sf = `${h2}/population_urban_Populstat/`;
	
	static config_obj;
	static input_config_json = `${this.bf}/populstat_config.json5`;
	static intermediate_cities_json = `${this.sf}/populstat_cities.json`;
	static intermediate_raw_cities_json = `${this.bf}/populstat_cities.json`;
	
	static A_getConfig () {
		//Declare local instance variables
		if (!this.config_obj)
			this.config_obj = JSON5.parse(fs.readFileSync(this.input_config_json));
		
		//Return statement
		return this.config_obj;
	}
	
	static B_getAllPopulstatTownLinks () {
		//Declare local instance variables
		let all_town_links = [];
		let config_obj = this.A_getConfig();
		
		//Iterate over config_obj.links
		for (let i = 0; i < config_obj.links.length; i++) {
			let local_link = config_obj.links[i].replace("http://", "")
				.replace("https://", "");
			
			if (local_link.split("/").length >= 3)
				if (local_link.endsWith("t.htm") || local_link.endsWith("t.html"))
					all_town_links.push(config_obj.links[i]);
		}
		
		//Return statement
		return all_town_links;
	}
	
	static async C_getAllPopulstatTownData () {
		if (fs.existsSync(this.intermediate_raw_cities_json))
			return JSON.parse(fs.readFileSync(this.intermediate_raw_cities_json, "utf8")); //Internal guard clause if intermediate raw cities file already exists
		
		//Declare local instance variables
		let all_populstat_town_links = this.B_getAllPopulstatTownLinks();
		let return_obj = {};
		
		//Iterate over all_populstat_town_links
		for (let i = 0; i < all_populstat_town_links.length; i++) {
			let local_key = all_populstat_town_links[i].split("/");
				local_key = local_key[local_key.length - 1]
					.replace("t.html", "")
					.replace("t.htm", "");
			
			return_obj[local_key] = await this.C_getPopulstatTownData(all_populstat_town_links[i]);
		}
		
		//Save populstat_cities
		fs.writeFileSync(this.intermediate_raw_cities_json, JSON.stringify(return_obj), "utf8");
		
		//Return statement
		return return_obj;
	}
	
	static async C_getPopulstatTownData (arg0_url) {
		//Convert from parameters
		let url = arg0_url;
		
		//Declare local instance variables
		let dom_obj = await JSDOM.fromURL(url);
		
		let dom_document = dom_obj.window.document;
		let return_obj = {};
		
		//Fetch the population table elements
		let is_population_body = false;
		let population_header = [];
		let population_table_el = dom_document.querySelector(`table[border=""]`);
			if (!population_table_el) return {}; //Internal guard clause if table is missing
		let population_table_rows = population_table_el.querySelectorAll("tr");
		
		//Iterate over all population_table_rows
		for (let i = 0; i < population_table_rows.length; i++)
			//Parse header - this should always be the zeroth row
			if (i === 0) {
				let all_cells = population_table_rows[i].querySelectorAll("td");
				let is_year_cell = false;
				
				for (let x = 0; x < all_cells.length; x++) {
					let first_number;
					let local_split_cell = all_cells[x].textContent.split("/");
					
					//Fetch the first number in the cell as the given year
					for (let y = 0; y < local_split_cell.length; y++)
						local_split_cell[y] = String.stripNonNumerics(local_split_cell[y]);
					for (let y = 0; y < local_split_cell.length; y++)
						if (!isNaN(parseInt(local_split_cell[y]))) {
							first_number = parseInt(local_split_cell[y]);
							break;
						} else {
							first_number = undefined;
							is_year_cell = false;
						}
					
					if (first_number !== undefined)
						is_year_cell = true;
					
					if (!is_year_cell) {
						population_header.push(all_cells[x].textContent);
					} else {
						population_header.push(first_number);
					}
				}
			} else {
				//Check if we have reached the population body
				let all_cells = population_table_rows[i].querySelectorAll("td");
				
				//Population body handling
				if (is_population_body) {
					if (all_cells.length === 1)
						continue;
					
					return_obj[all_cells[0].textContent] = {};
					let local_entry = return_obj[all_cells[0].textContent];
					
					//Set .name
					local_entry.name = all_cells[0].textContent;
					
					//Iterate over remaining cell data
					if (all_cells.length > 1)
						for (let x = 1; x < all_cells.length; x++) {
							let local_cell_content = all_cells[x].textContent;
							let local_header_name = population_header[x];
							
							//Populstat uses European decimal formatting
							let local_number_value = String.parseEuropeanNumber(local_cell_content);
							let local_value = (!isNaN(local_number_value)) ?
								local_number_value : local_cell_content;
							
							if (local_value !== "")
								local_entry[local_header_name] = local_value;
						}
				}
				
				//Check if we have reached the population body
				if (all_cells.length >= 1)
					if (all_cells[0].textContent.trim() === "")
						is_population_body = true;
			}
		
		//Return statement
		return return_obj;
	}
	
	static async D_loadPopulstatData () {
		//Declare local instance variables
		let populstat_obj = JSON.parse(fs.readFileSync(this.intermediate_raw_cities_json, "utf8"));
		
		//Iterate over populstat_obj
		Object.iterate(populstat_obj, (local_country_key, local_country_value) => {
			//Iterate over all cities in local_value
			Object.iterate(local_country_value, (local_city_key, local_city_value) => {
				try {
					let local_city_other_names;
					let local_city_population_obj = {};
					
					//1. Iterate over all city keys, handle population figures
					Object.iterate(local_city_value, (local_key, local_value) => {
						let is_population_key = false;
						
						//Other names handling
						if (local_key.startsWith(`variants `)) try {
							local_city_other_names = local_value.split(", ");
							delete local_city_value[local_key];
						} catch (e) {}
						
						//Population handling
						if (!isNaN(parseInt(local_key)) && !isNaN(parseFloat(local_value.toString())))
							is_population_key = true;
						if (is_population_key) {
							local_city_population_obj[local_key] = local_value;
							delete local_city_value[local_key];
						}
					});
					
					//2. Only cities with population figures should be kept
					if (Object.keys(local_city_population_obj).length > 0) {
						local_city_value.other_names = local_city_other_names;
						local_city_value.population = local_city_population_obj;
					} else {
						if (!local_city_value.population) delete local_country_value[local_city_key];
					}
				} catch (e) { console.error(e); }
			});
		});
		
		this.populstat_obj = populstat_obj;
		
		//Return statement
		return populstat_obj;
	}
	
	/**
	 * Wipes current Populstat coords so they can be re-geolocated.
	 * 
	 * @returns {Promise<Object>}
	 */
	static async E_cleanPopulstatCoords () {
		//Iterate over this.populstat_obj
		Object.iterate(this.populstat_obj, (local_country_key, local_country_value) => {
			Object.iterate(local_country_value, (local_city_key, local_city_value) => {
				if (typeof local_city_value === "object")
					delete local_city_value.coords;
			});
		});
		
		//Return statement
		return this.populstat_obj;
	}
	
	static async F_geolocateAllPopulstatCities () {
		//Declare local instance variables
		let config_obj = this.A_getConfig();
		
		let all_countries = Object.keys(config_obj.countries);
		
		Object.iterate(config_obj.countries, async (local_country_key, local_country_value, local_country_index) => {
			try {
				console.log(`Processing (${local_country_index + 1}/${all_countries.length}) ..`);
				await this.F_geolocatePopulstatCountryCities(local_country_key);
			} catch (e) { console.error(e); }
		});
	}
	
	static async F_geolocatePopulstatCountryCities (arg0_country_key) {
		//Convert from parameters
		let country_key = arg0_country_key;
		
		//Declare local instance variables
		let config_obj = this.A_getConfig();
		let country_obj = this.populstat_obj[country_key];
		
		let all_cities = Object.keys(country_obj);
		
		console.log(`Processing ${country_key} (${config_obj.countries[country_key]}), with ${all_cities.length} cities ..`);
		
		await Object.iterate(country_obj, async (local_city_key, local_city_value, local_city_index) => {
			try {
				//Save every 100 geolocated cities
				if (local_city_index % 100 === 0 && local_city_index !== 0) 
					fs.writeFileSync(this.intermediate_cities_json, JSON.stringify(this.populstat_obj), "utf8");
				
				let local_country_name = config_obj.countries[country_key];
					local_country_name = Array.toArray(local_country_name)[0];
				
				//Skip if coords already exist
				if (!local_city_value.coords) {
					console.log(`- ${local_city_value.name}`);
					
					if (local_city_value.name) {
						//.other_names handling
						let city_names = [`${local_city_value.name}, ${local_country_name}`];
						
						if (local_city_value.other_names)
							for (let i = 0; i < local_city_value.other_names.length; i++)
								city_names.push(`${local_city_value.other_names[i]}, ${local_country_name}`);
						
						console.log(` - Processing ${local_city_value.name}:`, city_names.join(", "));
						
						//Iterate over all city_names until a valid latlng coord is found
						for (let i = 0; i < city_names.length; i++) try {
							let local_coords = await Geospatiale.getGoogleMapsCityCoords(city_names[i]);
							
							if (local_coords[0] !== 0 && local_coords[1] !== 0) {
								console.log(` - Found ${city_names[i]} at (${local_coords[0]}, ${local_coords[1]}), (${i + 1}/${all_cities.length})`);
								local_city_value.coords = local_coords;
								break;
							} else {
								console.log(` - Failed to find ${city_names[i]} at (${local_coords[0]}, ${local_coords[1]}), (${i + 1}/${all_cities.length})`);
							}
						} catch (e) { console.error(e); }
					}
				}
			} catch (e) { console.error(e); }
		});
	}
	
	/**
	 * Removes duplicate coordinate pairs from `this.populstat_obj`.
	 * 
	 * @param {number} [arg0_precision=4]
	 * 
	 * @returns {string[]}
	 */
	static G_removeDuplicatePopulstatCoords (arg0_precision) {
		//Convert from parameters
		let precision = Math.returnSafeNumber(arg0_precision, 4);
		
		//Declare local instance variables
		let coords_dict = {};
		
		//Iterate over this.populstat_obj
		Object.iterate(this.populstat_obj, (local_country_key, local_country_value) => {
			Object.iterate(local_country_value, (local_city_key, local_city_value) => {
				if (local_city_value.coords) {
					let local_coords_string = JSON.stringify([
						Math.roundNumber(local_city_value.coords[0], precision),
						Math.roundNumber(local_city_value.coords[1], precision)
					]);
					
					if (!coords_dict[local_coords_string])
						coords_dict[local_coords_string] = [];
					coords_dict[local_coords_string].push(`${local_country_key}-${local_city_key}`);
				}
			});
		});
		
		//Iterate over coords_dict
		let remove_coords_keys = [];
		
		Object.iterate(coords_dict, (local_key, local_value) => {
			if (local_value.length > 1)
				remove_coords_keys = remove_coords_keys.concat(local_value);
		});
		
		//Iterate over this.populstat_obj
		Object.iterate(this.populstat_obj, (local_country_key, local_country_value) => {
			Object.iterate(local_country_value, (local_city_key, local_city_value) => {
				let local_key = `${local_country_key}-${local_city_key}`;
				
				if (remove_coords_keys.includes(local_key))
					delete local_city_value.coords;
			});
		});
		
		console.log(`Pruned ${remove_coords_keys.length} duplicate coordinate pairs.`);
		console.log(`- ${remove_coords_keys.join(", ")}`);
		
		//Return statement
		return remove_coords_keys;
	}
	
	static async process () {
		//Declare local instance variables; this.populstat_obj
		this.config_obj = this.A_getConfig();
		
		if (fs.existsSync(this.intermediate_cities_json)) {
			this.populstat_obj = JSON.parse(fs.readFileSync(this.intermediate_cities_json, "utf8"));
		} else {
			await this.C_getAllPopulstatTownData();
			await this.D_loadPopulstatData();
			await this.E_cleanPopulstatCoords();
			await this.F_geolocateAllPopulstatCities();
		}
		
		//Iterate over this.populstat_obj and normalise it
		let flattened_populstat_obj = {};
		
		Object.iterate(this.populstat_obj, (local_country_key, local_country_value) => {
			let local_country_name = this.config_obj.countries[local_country_key];
			
			Object.iterate(local_country_value, (local_city_key, local_city_value) => {
				if (local_city_value.population)
					local_city_value.population = Object.multiply(local_city_value.population, 1000);
				
				flattened_populstat_obj[`${local_city_key}-${local_country_name}`] = local_city_value;
			});
		})
		
		this.populstat_obj = flattened_populstat_obj;
		
		//Return statement
		return this.populstat_obj;
	}
};