global.population_urban_WorldCityPop = class {
	static _cache_dom;
	static input_population_html = `${h1}/population_urban_WorldCityPop/_worldcitypop.htm`;
	static intermediate_worldcitypop_json = `${h2}/population_urban_WorldCityPop/worldcitypop.json`;
	static worldcitypop_obj;
	
	static async A_getWorldCityPopObject () {
		//Declare local instance variables
		let jsdom_obj = (this._cache_dom) ? 
			this._cache_dom : new JSDOM(fs.readFileSync(this.input_population_html, "utf8"));
		let world_city_pop_dom = jsdom_obj.window.document;
		
		//Cache extracted DOM; select table_el
		if (!this._cache_dom) this._cache_dom = jsdom_obj;
		let pop_dataframe = HTML.getTableAsDataframe(
			world_city_pop_dom.querySelector(`table#tbl`), 
			{ property: "textContent" }
		);
		let pop_dataframe_html = HTML.getTableAsDataframe(
			world_city_pop_dom.querySelector(`table#tbl`),
			{ property: "innerHTML" }
		);
		let pop_dataframe_header = pop_dataframe[0];
		let pop_obj = {};
		
		//Attempt parseInt on numeric headers
		for (let i = 0; i < pop_dataframe_header.length; i++)
			if (!isNaN(parseInt(pop_dataframe_header[i])))
				pop_dataframe_header[i] = parseInt(pop_dataframe_header[i]);
		
		//Iterate over all rows in pop_dataframe after header
		for (let i = 1; i < pop_dataframe.length; i++) {
			let local_key = `${pop_dataframe[i][0]}-${pop_dataframe[i][1]}`;
			let local_population_obj = {};
			
			//Iterate over all years
			for (let x = 2; x < pop_dataframe[i].length; x++) {
				let local_html = pop_dataframe_html[i][x];
				let local_value = parseInt(pop_dataframe[i][x].replaceAll(",", ""));
				
				if ((local_html && local_html.startsWith("<a") && local_value > 0) || local_value === 0)
					if (!isNaN(local_value))
						local_population_obj[pop_dataframe_header[x]] = local_value;
			}
			local_population_obj = Object.expandValue(local_population_obj, {
				expand_max: false,
				value: 0 
			});
			
			pop_obj[local_key] = {
				name: pop_dataframe[i][0],
				
				country: pop_dataframe[i][1],
				key: local_key,
				population: local_population_obj
			};
		}
		
		//Return statement
		return pop_obj;
	}
	
	static async B_geolocateWorldCityPopObject () {
		if (fs.existsSync(this.intermediate_worldcitypop_json)) { //Internal guard clause 
			this.worldcitypop_obj = JSON.parse(fs.readFileSync(this.intermediate_worldcitypop_json, "utf8"));
			return this.worldcitypop_obj;
		}
			
		//Declare local instance variables
		let world_city_pop_obj = await this.A_getWorldCityPopObject();
		console.log(`Fetched world_city_pop_obj.`);
		
		//Iterate over world_city_pop_obj
		let all_cities = Object.keys(world_city_pop_obj);
		
		for (let i = 0; i < all_cities.length; i++) {
			let local_value = world_city_pop_obj[all_cities[i]];
			
			local_value.coords = await Geospatiale.getGoogleMapsCityCoords(`${local_value.name}, ${local_value.country}`, {
				google_maps_api_key: svea_settings.gmaps_api_key
			});
			world_city_pop_obj[all_cities[i]] = local_value;
			console.log(`Gmaps (${i}/${all_cities.length}): Geolocated ${local_value.name}, ${local_value.country}:`, local_value.coords);
		}
		
		fs.writeFileSync(this.intermediate_worldcitypop_json, JSON.stringify(world_city_pop_obj), "utf8");
		console.log(`Wrote geolocated file to (1/2): ${this.intermediate_worldcitypop_json}`);
		
		//Iterate over world_city_pop_obj to geolocate [0, 0] cities using OSM
		for (let i = 0; i < all_cities.length; i++) {
			let local_value = world_city_pop_obj[all_cities[i]];
			
			if (local_value.coords)
				if (local_value.coords[0] === 0 && local_value.coords[1] === 0) {
					local_value.coords = await Geospatiale.getOSMCityCoords(`${local_value.name}`);
					
					world_city_pop_obj[all_cities[i]] = local_value;
					console.log(`OSM (${i}/${all_cities.length}): Geolocated ${local_value.name}, ${local_value.country}:`, local_value.coords);
				}
		}
		
		fs.writeFileSync(this.intermediate_worldcitypop_json, JSON.stringify(world_city_pop_obj), "utf8");
		console.log(`Wrote geolocated file to (2/2): ${this.intermediate_worldcitypop_json}`);
		
		this.worldcitypop_obj = world_city_pop_obj;
		
		//Return statement
		return world_city_pop_obj;
	}
	
	static async C_getHybridObject () {
		let old_world_city_pop_obj = await this.B_geolocateWorldCityPopObject();
		let new_world_city_pop_obj = await this.A_getWorldCityPopObject();
		let return_obj = {};
		
		//Iterate over old_world_city_pop_obj and merge it with new_world_city_pop_obj corresponding entries
		Object.iterate(old_world_city_pop_obj, (old_city_key, old_city_obj) => {
			return_obj[old_city_key] = {
				...old_city_obj,
				...new_world_city_pop_obj[old_city_key]
			};
		});
		
		fs.writeFileSync(this.intermediate_worldcitypop_json, JSON.stringify(return_obj), "utf8");
		console.log(`Wrote hybrid object file: ${this.intermediate_worldcitypop_json}`);
		
		this.worldcitypop_obj = return_obj;
		
		//Return statement
		return return_obj;
	}
	
	static async processRasters () {
		//1. Fetch world city population object
		await this.C_getHybridObject();
		
		//Return statement
		return this.worldcitypop_obj;
	}
};