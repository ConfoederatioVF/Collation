/**
 * ##### Constructor:
 * - `arg0_options`: {@link Object}
 *   - `.blacklisted_regions`: {@link Array}<{@link string}>
 *   - `.top_regions`: {@link number} - How many of the top regions to draw. -1 by default.
 * 
 * @type {GLOBAL_Liveuamap_Worker}
 */
global.GLOBAL_Liveuamap_Worker = class {
	//Defines
	static _update_regions_interval = 86400*7; //Update auto-cached regions once a week
	
	//Paths
	static bf = `${l2}GLOBAL_Liveuamap/`;
	static input_auto_regions_json = `${this.bf}Liveuamap_auto_regions.json`;
	static input_chrome_profile = `C:/Users/htmlp/AppData/Local/Google/Chrome/User Data/Profile 1`;
	static input_manual_regions_json = `${this.bf}Liveuamap_regions.json5`;
	
	//Workers
	static workers = {};
	
	constructor (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		if (!options.top_regions) options.top_regions = Math.returnSafeNumber(options.top_regions, -1);
		
		//Declare local instance variables
		this.options = options;
		this.static = GLOBAL_Liveuamap_Worker;
		
		this.browser = new Blacktraffic.AgentBrowserPuppeteer(undefined, {
			user_data_folder: this.static.input_chrome_profile,
			onload: async () => {
				await this.draw();
			}
		});
	}
	
	async draw () {
		//Declare local instance variables
		let all_regions = await this.static.getLiveuamapRegions();
		let liveuamap_tab = await this.browser.openTab("liveuamap");
		let regions_threshold = (this.options.top_regions > 0) ? 
			this.options.top_regions : all_regions.length;
		
		this.layer = new maptalks.VectorLayer("liveuamap").addTo(map);
		
		//0. Load pre-load scripts
		this.browser.injectScriptOnload(liveuamap_tab, this.static._captureLeaflet);
		
		//Iterate over all_regions until regions_threshold
		for (let i = 0; i < regions_threshold; i++) {
			let local_region = all_regions[i];
			
			console.log(`Plotting ${local_region.name} ..`);
			await liveuamap_tab.goto(local_region.url, { waitUntil: "networkidle2" });
			await Blacktraffic.sleep(Math.randomNumber(1000, 3000));
			//Check to see if there is a modal stating it is paid
			let is_paid = await liveuamap_tab.$eval(`.modalWrapCont`, (el) => {
				if (el && el.innerHTML) if (el.innerHTML.includes("in free version")) 
					return true;
			});
			
			if (!is_paid) {
				let geometries = await liveuamap_tab.evaluate(function () {
					//Declare functions
					let getGeometryType = (geometry) => {
						if (geometry instanceof L.Polygon) {
							return 'polygon';
						} else if (geometry instanceof L.Polyline) {
							// Note: Polygons are instances of Polylines, 
							// so we check Polygon first.
							return 'line';
						} else if (geometry instanceof L.Marker || geometry instanceof L.CircleMarker) {
							return 'point';
						}
					};
					
					//Declare local instance variables
					let current_map = getMaps()[0];
					
					let all_geometry_keys = Object.keys(current_map._layers);
					let geometries = [];
					
					//Iterate over all_geometry_keys in the given layer
					for (let i = 0; i < all_geometry_keys.length; i++) {
						let local_geometry = current_map._layers[all_geometry_keys[i]];
						let local_geometry_type = getGeometryType(local_geometry);
						let local_options = local_geometry.options;
						
						//Polygon handling
						if (["polygon", "line"].includes(local_geometry_type)) {
							geometries.push({
								geometry: local_geometry.toGeoJSON(),
								symbol: {
									polygonFill: local_options.fillColor,
									polygonOpacity: parseFloat(local_options.fillOpacity),
									
									lineColor: local_options.color,
									lineOpacity: parseFloat(local_options.opacity),
									lineWidth: parseFloat(local_options.weight)
								},
								
								type: local_geometry_type
							});
						} else if (local_geometry_type === "point") {
							let local_icon;
								try { local_icon = local_geometry._icon.getAttribute("src"); } catch (e) {}
							
							geometries.push({
								geometry: local_geometry.toGeoJSON(),
								symbol: {
									markerDx: 0,
									markerDy: 0,
									markerHeight: 24,
									markerOpacity: 1,
									markerWidth: 24,
									markerFile: local_icon
								},
								
								type: local_geometry_type
							});
						}
					}
					
					console.log(geometries);
					
					//Return statement
					return geometries;
				});
				
				//Plot geometries on map
				for (let i = 0; i < geometries.length; i++) {
					let local_geometry = maptalks.GeoJSON.toGeometry(geometries[i].geometry);
						local_geometry.updateSymbol(geometries[i].symbol);
						local_geometry.addTo(this.layer);
				}
				
				await Blacktraffic.sleep(10000, 15000); //10s-15s delay between polling
			}
		}
	}
	
	remove () {
		
	}
	
	static _captureLeaflet = function () {
		(function () {
			"use strict";
			
			// This array will hold all map instances found on the page
			window.captured_maps = [];
			
			let leafletBackend;
			
			// We define a getter/setter on window.L to catch the moment Leaflet loads
			Object.defineProperty(window, "L", {
				get: function () {
					return leafletBackend;
				},
				set: function (newLeaflet) {
					leafletBackend = newLeaflet;
					
					// Ensure we have the Map object and haven't hooked it yet
					if (leafletBackend && leafletBackend.Map && !leafletBackend._hooked) {
						leafletBackend._hooked = true;
						
						console.log("Leaflet detected! Injecting initialization hook...");
						
						leafletBackend.Map.addInitHook(function () {
							window.captured_maps.push(this);
							console.log("New Leaflet map instance captured:", this);
						});
					}
				},
				configurable: true,
			});
			
			// Optional: Expose a helper function to the console to interact with maps
			window.getMaps = () => window.captured_maps;
		})();
	}
	
	/**
	 * Caches current Livemap regions to Liveuamap_auto_regions.json5
	 */
	static async getLiveuamapRegions () {
		//Declare local instance variables
		let input_json_path = GLOBAL_Liveuamap_Worker.input_auto_regions_json;
		let last_modified = File.getLastModified(input_json_path);
		let refresh_cache = false;
		
		//Check whether the cache should be refreshed
		if (last_modified === undefined || last_modified.seconds >= GLOBAL_Liveuamap_Worker._update_regions_interval)
			refresh_cache = true;
		
		if (!refresh_cache) {
			//Return statement
			return JSON.parse(fs.readFileSync(input_json_path, "utf8"));
		} else {
			//Open a new browser instance and navigate to liveuamap.com
			let temp_browser = new Blacktraffic.AgentBrowserPuppeteer("liveuamap_regions", {
				user_data_folder: this.input_chrome_profile,
				onload: async () => {
					let liveuamap_tab = await temp_browser.openTab("liveuamap");
					//0. Load pre-load scripts
					temp_browser.injectScriptOnload(liveuamap_tab, this._captureLeaflet);
					
					//1. Navigate to Liveuamap; click on language
					let _language_selector = `a#menu_languages`;
					
					await liveuamap_tab.goto("https://liveuamap.com/", { waitUntil: "networkidle2" });
					await liveuamap_tab.waitForSelector(_language_selector);
					await liveuamap_tab.click(_language_selector);
					
					let regions_els = await liveuamap_tab.$$eval(`div.rg-list > a`, (els) => {
						return els.map((el) => ({
							name: el.getAttribute("title"),
							url: el.href
						}));
					});
					
					//Write file to input_json_path
					await fs.writeFile(input_json_path, JSON.stringify(regions_els), (err) => {
						if (err) console.error(err);
					});
					await temp_browser.remove();
				}
			});
		}
	}
};