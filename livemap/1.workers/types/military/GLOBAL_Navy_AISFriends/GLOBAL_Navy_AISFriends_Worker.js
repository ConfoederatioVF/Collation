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
		//Declare local instance variables
		let all_vessels = await this.fetchVesselData();
		let geometries = [];
		
		for (let i = 0; i < all_vessels.length; i++) try {
			if (Date.getDaysAgo(all_vessels[i].timestamp_of_position) > this.options.days_ago_threshold) continue; //Internal guard clause for recency
			
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
			geometries.push(local_marker);
		} catch (e) { console.error(e); }
		
		this.geometries = geometries;
		
		//Return statement
		return geometries;
	}
	
	async fetchVesselData () {
		const targetUrl =
			"https://www.aisfriends.com/vessels/bounding-box?lon_min=-180&lat_min=-90&lon_max=180&lat_max=90&zoom=12&types=4";
		
		// List of proxies to try in order
		const proxyAttempts = [
			`https://corsproxy.io/?${encodeURIComponent(targetUrl)}`,
			`https://api.allorigins.win/get?url=${encodeURIComponent(targetUrl)}`,
		];
		
		for (const url of proxyAttempts) {
			try {
				console.log(`Attempting fetch via: ${url}`);
				const response = await fetch(url, {
					method: "GET",
					headers: {
						Accept: "application/json",
					},
				});
				
				if (!response.ok) throw new Error(`Status ${response.status}`);
				
				let data = await response.json();
				
				// AllOrigins wraps content in a .contents string, others return raw JSON
				if (data && data.contents) {
					try {
						data = JSON.parse(data.contents);
					} catch (e) {
						/* Not JSON string */
					}
				}
				
				if (Array.isArray(data)) return data;
				if (data && Array.isArray(data.vessels)) return data.vessels;
			} catch (err) {
				console.warn(`Proxy failed (${url}): ${err.message}`);
				// Continue to next proxy in the loop
			}
		}
		
		// FINAL FALLBACK: If all proxies fail, the browser console cannot bypass Cloudflare's 
		// VPN block. We return an empty array to prevent the script from crashing.
		console.error("All fetch attempts failed (403/522). Cloudflare is blocking the VPN/Proxies.");
		return [];
	}
};