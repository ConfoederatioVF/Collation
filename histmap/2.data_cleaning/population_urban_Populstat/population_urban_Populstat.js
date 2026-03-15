global.population_urban_Populstat = class {
	static bf = `${h1}/population_urban_Populstat/`;
	
	static config_obj;
	static input_config_json = `${this.bf}/populstat_config.json5`;
	static intermediate_cities_json = `${this.bf}/populstat_cities.json`;
	
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
					all_town_links.push(local_link[i]);
		}
		
		//Return statement
		return all_town_links;
	}
	
	static async C_getAllPopulstatTownData () {
		
	}
	
	static async C_getPopulstatTownData () {
		
	}
	
	static async D_loadPopulstatData () {
		
	}
	
	static async E_cleanPopulstatCoords () {
		
	}
	
	static async F_geolocateAllPopulstatCities () {
		
	}
	
	static async F_geolocatePopulstatCountryCities (arg0_country_key) {
		
	}
	
	static async G_removeDuplicatePopulstatCoords () {
		
	}
};