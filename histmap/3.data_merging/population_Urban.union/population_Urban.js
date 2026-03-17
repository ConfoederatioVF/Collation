global.population_Urban = class {
	static bf = `${h3}/population_Urban.union/`;
	static chandler_modelski_obj;
	static intermediate_chandler_modelski_json = `${this.bf}/chandler_modelski_cities.json`;
	
	/**
	 * Returns Chandler-Modelski cities within a range of target [lat, lng] coords.
	 * 
	 * @param {number[]} arg0_coords
	 * @param {Object} [arg1_options]
	 *  @param {number} [arg1_options.precision=5] - The latlng merge precision between Worldcitypop (GT) and Chandler-Modelski (RR). Haversine distance (km).
	 * 
	 * @returns {Promise<string[]>}
	 * @private
	 */
	static async _getChandlerModelskiCitiesInRange (arg0_coords, arg1_options) {
		//Convert from parameters
		let coords = (arg0_coords) ? arg0_coords : [0, 0];
		let options = (arg1_options) ? arg1_options : {};
		
		//Initialise options
		options.precision = Math.returnSafeNumber(options.precision, 5); //5km distance
		
		//Declare local instance variables
		let chandler_modelski_obj = (options.chandler_modelski_obj) ?
			options.chandler_modelski_obj : await population_urban_ChandlerModelski.processRasters();
		let duplicate_keys = [];
		
		//Iterate over chandler_modelski_obj; find cities in range of options.coords
		Object.iterate(chandler_modelski_obj, (local_key, local_value) => {
			let local_coords = [
				Math.returnSafeNumber(local_value?.latitude), 
				Math.returnSafeNumber(local_value?.longitude)
			];
			
			//Switch from latlng to lnglat for Haversine compute
			let local_distance = Geospatiale.haversineDistance(
				[local_coords[1], local_coords[0]],
				[coords[1], coords[0]]
			);
			
			if (local_distance < options.precision)
				duplicate_keys.push(local_key);
		});
		
		//Return statement
		return duplicate_keys;
	}
	
	/**
	 * Returns a normalised Chandler-Modelski object free of transcription errors.
	 * 
	 * @param {Object} [arg0_options]
	 *  @param {number} [arg0_options.precision=5]
	 * 
	 * @returns {Promise<Object>}
	 */
	static async A_getChandlerModelskiObject (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Declare local instance variables
		let chandler_modelski_obj = await population_urban_ChandlerModelski.processRasters();
		let return_obj = {};
		let worldcitypop_obj = await population_urban_WorldCityPop.processRasters();
		
		//Iterate over worldcitypop_obj and interpolate chandler_modelski_obj into it (Object.interpolateGT)
		await Object.iterate(worldcitypop_obj, async (local_key, local_value) => {
			if (local_value.coords && local_value.population) {
				let chandler_modelski_duplicate_keys = await this._getChandlerModelskiCitiesInRange(local_value.coords, {
					precision: options.precision
				});
				let local_population = structuredClone(local_value.population);
				
				//Iterate over all chandler_modelski_duplicate_keys and merge their RRs into GT
				for (let i = 0; i < chandler_modelski_duplicate_keys.length; i++) {
					let local_city = chandler_modelski_obj[chandler_modelski_duplicate_keys[i]];
					let local_population_keys = Object.keys(local_city.population).map(Number);
					
					//Iterate over local_population, if RR is less than the equivalent GT, average GT with RR
					Object.iterate(local_population, (local_population_key, local_population_value) => {
						let gt_population = local_population_value;
						let rr_population_obj = Object.linearInterpolation(local_city.population, { 
							years: [parseInt(local_population_key)] 
						});
						let rr_population = Math.returnSafeNumber(rr_population_obj[local_population_key]);
						
						if (gt_population !== undefined)
							if (gt_population > rr_population && rr_population !== 0)
								local_population[local_population_key] = (gt_population + rr_population)/2;
					});
					
					local_population = Object.interpolateGT(local_population, local_city.population);
					local_population = Object.operate(local_population, `Math.round(n)`);
				}
				
				//If GT is before first non-interpolated value, is interpolated, and has a population >=100k, delete the value
				Object.iterate(local_population, (local_population_key, local_population_value) => {
					if (local_value.links && local_value.links.length > 0)
						if (parseInt(local_population_key) < local_value.links[0] && local_population_value >= 100000 && local_value.is_interpolated)
							delete local_population[local_population_key];
				});
				
				let new_city_obj = structuredClone(local_value);
					new_city_obj.latitude = local_value.coords[0];
					new_city_obj.longitude = local_value.coords[1];
					new_city_obj.population = local_population;
				
				return_obj[local_key] = new_city_obj;
			}
		});
		
		//Return statement
		return return_obj;
	}
	
	static async processRasters () {
		this.chandler_modelski_obj = await this.A_getChandlerModelskiObject();
		fs.writeFileSync(this.intermediate_chandler_modelski_json, JSON.stringify(this.chandler_modelski_obj, null, 2), "utf8");
	}
};