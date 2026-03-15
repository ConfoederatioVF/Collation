global.population_urban_ChandlerModelski = class {
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
							let local_year = parseInt(local_subkey.replace("ad_", ""))*-1;
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
		
		//Return statement
		return chandler_modelski_obj;
	}
};