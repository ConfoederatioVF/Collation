global.GLOBAL_Navy_AISFriends_Worker = class {
	constructor (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		options.days_ago_threshold = Math.returnSafeNumber(options.days_ago_threshold, 7);
		
		//Declare local instance variables
		this.options = options;
		this.static = GLOBAL_Navy_AISFriends_Worker;
		this.draw();
	}
	
	async draw () {
		let all_vessels = await this.fetchVesselData();
		this.layer = new maptalks.VectorLayer("AISFriends").addTo(map);
		
		for (let i = 0; i < all_vessels.length; i++) try {
			if (this.getDaysAgo(all_vessels[i].timestamp_of_position) > this.options.days_ago_threshold) continue; //Internal guard clause for recency
			
			let local_marker = new maptalks.Marker([all_vessels[i].longitude, all_vessels[i].latitude], {
				symbol: [{
					markerFile: "./gfx/icons/naval_vessel.png",
					markerHeight: 32,
					markerWidth: 32,
				}, {
					textDy: (32 + 8)*-1,
					textName: (all_vessels[i].name) ? `${all_vessels[i].name} (${all_vessels[i].flag})` : `${all_vessels[i].flag} Military Vessel`,
					
					textFaceName: "Karla",
					textFill: "white",
					textHaloFill: "black",
					textHaloRadius: 2,
					textSize: 11
				}]
			});
			local_marker.addTo(this.layer);
		} catch (e) { console.error(e); }
	}
	
	getDaysAgo (arg0_timestamp) {
		//Convert from parameters
		let timestamp = arg0_timestamp;
		
		// Current time in milliseconds
		const now = Date.now();
		
		// Convert input timestamp from seconds to milliseconds
		const targetTime = timestamp * 1000;
		
		// Calculate the difference in milliseconds
		const differenceInMs = now - targetTime;
		
		// Define constants for time conversion
		const msInADay = 1000 * 60 * 60 * 24;
		
		// Calculate days and round down to the nearest whole number
		const daysAgo = Math.floor(differenceInMs / msInADay);
		
		return daysAgo;
	}
	
	async fetchVesselData () {
		const url =
			"https://www.aisfriends.com/vessels/bounding-box?lon_min=-180&lat_min=-90&lon_max=180&lat_max=90&zoom=12&types=4";
		
		try {
			const response = await fetch(url, {
				method: "GET",
				headers: {
					Accept: "application/json",
					"User-Agent": "Node.js Script",
				},
			});
			
			// Check if the request was successful
			if (!response.ok) {
				throw new Error(`HTTP error! Status: ${response.status}`);
			}
			
			// Parse the response body as JSON
			const data = await response.json();
			
			// Now 'data' is your Array<Object>
			console.log("Successfully retrieved data:");
			console.log(data);
			
			return data;
		} catch (error) {
			console.error("Error fetching or parsing data:", error.message);
		}
	}
};