global.population_urban_ChandlerModelski = class {
	static chandler_modelski_obj;
	static input_folder = `${h1}/population_urban_ChandlerModelski/`;
	
	static async A_getCSVs () {
		//Declare local instance variables
		let all_csv_files = [];
		let all_files = await File.getAllFiles(this.input_folder);
		
		//Iterate over all_files
		for (let i = 0; i < all_files.length; i++)
			if (File.isFile(all_files[i]) && all_files[i].endsWith(".csv"))
				all_csv_files.push(all_files[i]);
		
		//Return statement
		return all_csv_files;
	}
	
	static async B_getChandlerModelskiObject () {
		//Declare local instance variables
		let all_csv_files = await this.A_getCSVs();
		let chandler_modelski_obj = {};
		
		//Iterate over all_csv_files
		for (let i = 0; i < all_csv_files.length; i++) {
			let csv_obj = File.loadCSVAsJSON(all_csv_files[i]);
			
			Object.iterate(csv_obj, (local_key, local_value) => {
				let local_city_key = local_key.trim();
				let temp_city_obj = {
					population: {}
				};
				
				//Iterate over local_value (CSV columns)
				Object.iterate(local_value, (local_subkey, local_subvalue) => {
					local_subkey = local_subkey.toLowerCase();
					local_subvalue = (Array.isArray(local_subvalue)) ? local_subvalue[0] : local_subvalue;
					
					if (local_subvalue !== "")
						if (local_subkey === "city") {
							temp_city_obj.name = local_subvalue.trim();
						} else if (local_subkey === "othername") {
							temp_city_obj.other_names = local_subvalue.split(",");
						} else if (local_subkey === "country") {
							temp_city_obj.country = local_subvalue;
						} else if (local_subkey === "latitude") {
							temp_city_obj.latitude = parseFloat(local_subvalue);
						} else if (local_subkey === "longitude") {
							temp_city_obj.longitude = parseFloat(local_subvalue);
						} else if (local_subkey === "certainty") {
							temp_city_obj.certainty = parseInt(local_subvalue);
						} else if (local_subkey.startsWith("bc_")) {
							let local_year = parseInt(local_subkey.replace("bc_", ""))*-1;
							temp_city_obj.population[local_year] = parseInt(local_subvalue);
						} else if (local_subkey.startsWith("ad_")) {
							let local_year = parseInt(local_subkey.replace("ad_", ""));
							temp_city_obj.population[local_year] = parseInt(local_subvalue);
						}
				});
				
				local_city_key = `${local_city_key}-${temp_city_obj.country}`;
				if (!chandler_modelski_obj[local_city_key]) {
					chandler_modelski_obj[local_city_key] = temp_city_obj;
				} else {
					let local_city_obj = chandler_modelski_obj[local_city_key];
					
					Object.iterate(temp_city_obj.population, (local_subkey, local_subvalue) => {
						if (!local_city_obj.population[local_subkey]) {
							local_city_obj.population[local_subkey] = local_subvalue;
						} else {
							let local_merged_value = local_city_obj.population[local_subkey];
							
							if (!Array.isArray(local_merged_value))
								local_city_obj.population[local_subkey] = [local_merged_value];
							local_city_obj.population[local_subkey].push(local_subvalue);
						}
					});
				}
			});
		}
		
		//Iterate over all merged cities and take the geomean of any population arrays
		Object.iterate(chandler_modelski_obj, (city_key, city_obj) =>
			Object.iterate(city_obj.population, (year_key, pop_value) => {
				if (Array.isArray(pop_value))
					city_obj.population[year_key] = Math.weightedGeometricMean(pop_value);
			}));
		
		this.chandler_modelski_obj = chandler_modelski_obj;
		
		//Return statement
		return this.chandler_modelski_obj;
	}
	
	static async process () {
		//Declare local instance variables
		if (!this.chandler_modelski_obj) await this.B_getChandlerModelskiObject();
			let chandler_modelski_obj = this.chandler_modelski_obj;
		
		//Set manual fixes; these are mostly clerical errors regarding accidental 0 entries or order of magnitude errors
		//Aleppo, Syria
		delete chandler_modelski_obj["Aleppo-Syria"].population["1300"]; //0 entry
		//Alexandria, Egypt
		chandler_modelski_obj["Alexandria-Egypt"].population["365"] = chandler_modelski_obj["Alexandria-Egypt"].population["361"]; //Alexandrian earthquake is on the wrong year
		delete chandler_modelski_obj["Alexandria-Egypt"].population["361"]; //361 entry
		//Algiers, Algeria
		chandler_modelski_obj["Algiers-Algiers"].population["1925"] = 222000; //10x error
		chandler_modelski_obj["Algiers-Algeria"] = chandler_modelski_obj["Algiers-Algiers"]; //Algiers is not a country
		chandler_modelski_obj["Algiers-Algeria"].country = "Algeria";
		delete chandler_modelski_obj["Algiers-Algiers"];
		//Augsburg, Germany
		chandler_modelski_obj["Augsburg-Germany"] = chandler_modelski_obj["Augsberg-Germany"]; //Fix name
		chandler_modelski_obj["Augsburg-Germany"].name = "Augsburg";
		chandler_modelski_obj["Augsburg-Germany"].other_names.push("Augsberg");
		delete chandler_modelski_obj["Augsberg-Germany"];
		//Birmingham, United States of America
		//chandler_modelski_obj["Birmingham-United States of America"].population["1970"] = 300910; //Confused with Birmingham, United Kingdom
		//Delhi, India
		chandler_modelski_obj["Delhi-India"].population["1375"] = 200000; //10x error
		chandler_modelski_obj["Delhi-India"].population["1399"] = 25000; //Tamurlane sacking
		chandler_modelski_obj["Delhi-India"].population["1596"] = 80000; //10x error
		//Fez, Morocco
		chandler_modelski_obj["Fez-Morocco"].population["1800"] = 60000; //Weird noise drop
		//Goa, India
		delete chandler_modelski_obj["Goa-India"].population["1510"]; //Remove noise
		//Izmail, Ukraine
		chandler_modelski_obj["Izmail-Ukraine"] = chandler_modelski_obj["Izmail-Romania"]; //Izmail is in Ukraine, not Romania
		delete chandler_modelski_obj["Izmail-Romania"];
		//Lahore, Pakistan
		chandler_modelski_obj["Lahore-Pakistan"].population["1600"] = 200000; //Sack of Lahore wasn't that devastating
		chandler_modelski_obj["Lahore-Pakistan"].population["1622"] = 250000;
		chandler_modelski_obj["Lahore-Pakistan"].population["1627"] = 255000;
		chandler_modelski_obj["Lahore-Pakistan"].population["1631"] = 284000;
		//Nanjing, China
		chandler_modelski_obj["Nanjing-China"].population["1970"] = 2000000; //10x error
		chandler_modelski_obj["Nanjing-China"].population["2000"] = 5448900; //Demonstrably false
		//Palermo, Italy
		chandler_modelski_obj["Palermo-Italy"].population["1150"] = 125000; //1000x error
		//Philadelphia, United States of America
		chandler_modelski_obj["Philadelphia-United States of America"].population["1914"] = 1760000; //10x error
		//Skopje, Macedonia
		chandler_modelski_obj["Skopje-Macedonia"] = chandler_modelski_obj["Skopje-Serbia"]; //Skopje is in Macedonia, not Serbia
		delete chandler_modelski_obj["Skopje-Serbia"];
		//Srirangapatna, India
		chandler_modelski_obj["Srirangapatna-India"].population["1780"] = 38000; //This figure is too high
		chandler_modelski_obj["Srirangapatna-India"].population["1799"] = 50000; //This figure is too high
		//Tbilisi, Georgia
		delete chandler_modelski_obj["Tbilisi-Georgia"].population["1100"]; //Zero entry
		//Tokyo, Japan
		delete chandler_modelski_obj["Tokyo-Japan"].population["2000"]; //Erroneous entry
		
		//Remove any values after 1975
		Object.iterate(chandler_modelski_obj, (local_key, local_value) => {
			if (local_value?.population) {
				Object.iterate(local_value.population, (local_population_key, local_population_value) => {
					if (parseInt(local_population_key) > 1975)
						delete local_value.population[local_population_key];
				});
				
				if (Object.keys(local_value.population).length === 0)
					delete chandler_modelski_obj[local_key];
			}
		});
		
		this.chandler_modelski_obj = chandler_modelski_obj;
		
		//Return statement
		return this.chandler_modelski_obj;
	}
};