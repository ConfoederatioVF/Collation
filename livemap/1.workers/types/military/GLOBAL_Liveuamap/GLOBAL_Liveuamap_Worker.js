global.GLOBAL_Liveuamap_Worker = class extends Blacktraffic.Worker {
	static bf = `${l1m}GLOBAL_Liveuamap/`;
	static input_auto_regions_json = path.join(this.bf, "Liveuamap_auto_regions.json");
	static _update_regions_interval = 86400*7;
	
	constructor(arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		options.interval = Math.returnSafeNumber(options.interval, 3600);
		super("Liveuamap", {
			...options,
			interval: 0,
			do_not_close_tab: true,
			log_channel: "Liveuamap_Scraper",
		});
		
		//Declare local instance variables
		this.options = options;
		this.static = GLOBAL_Liveuamap_Worker;
		
		//Start worker
		if (this.is_enabled && this.options.interval > 0) 
			this.startInterval();
	}
	
	async execute (arg0_tab, arg1_instance) {
		//Convert from parameters
		let tab = arg0_tab;
		let instance = arg1_instance;
		
		//Declare local instance variables
		let all_regions = await this.getLiveuamapRegions();
		let ontologies = [];
		let regions_threshold = Math.returnSafeNumber(this.options.top_regions, all_regions.length);
		let webapi = Blacktraffic.AgentBrowser.webapi;
		
		if (!tab._scripts_injected) {
			await tab.evaluateOnNewDocument(webapi.Leaflet.captureMaps);
			tab._scripts_injected = true;
		}
		
		//Iterate over all regions within regions_threshold
		for (let i = 0; i < regions_threshold; i++) {
			try {
				let local_region = all_regions[i];
				if (!local_region) continue;
				
				this.log(`[${i + 1}/${regions_threshold}] Polling region: ${local_region.name} ..`);
				
				//Check if region is paid
				await tab.goto(local_region.url, { waitUntil: "networkidle2" });
				await Blacktraffic.sleep(Math.randomNumber(2000, 4000));
				
				let is_paid = await tab.evaluate(() => {
					let modal = document.querySelector(`.modalWrapCont`);
					
					//Return statement
					return modal?.innerHTML.includes("in free version");
				});
				
				if (is_paid) {
					this.warn(`Skipping ${local_region.name}: Blocked by free version limit.`);
					continue;
				}
				
				//Evaluate geometries
				let geometries = await tab.evaluate(function () {
					//Declare local instance variables
					let results = [];
					let return_obj = {
						polygon: [],
						line: [],
						point: []
					};
					
					try {
						let current_map = getMaps()[0];
						let layers = current_map._layers;
						
						//Iterate over all layers
						let all_layers = Object.keys(layers);
						let content_ids = [];
						
						for (let i = 0; i < all_layers.length; i++) {
							let local_geometry = layers[all_layers[i]];
							if (local_geometry.toGeoJSON === undefined) continue;
							
							let fields_obj = {};
							let local_html;
							let local_options = (local_geometry.options) ? local_geometry.options : {};
							let local_type = webapi.Leaflet.getGeometryType(local_geometry);
							let symbol_obj = {};
							
							//Line/Polygon/Point handling
							if (["line", "polygon"].includes(local_type)) {
								symbol_obj = {
									polygonFill: local_options.fillColor,
									polygonOpacity: parseFloat(local_options.fillOpacity),
									lineColor: local_options.color,
									lineOpacity: parseFloat(local_options.opacity),
									lineWidth: parseFloat(local_options.weight)
								}
							} else if (local_type === "point") {
								let leaflet_id = local_geometry?._leaflet_id;
								
								if (leaflet_id !== undefined && window.markers)
									for (let x = 0; x < window.markers.length; x++) {
										let local_id = window.markers[x]?.m?._leaflet_id;
										
										if (local_id === leaflet_id && window.markers[x]?.v?.timestamp !== undefined) {
											let local_value = window.markers[x].v;
											
											//Set defined fields_obj
											fields_obj.image = local_value.picture;
											fields_obj.source = local_value.source;
											if (local_value.moreSources)
												fields_obj.source = fields_obj.source.concat(local_value.moreSources);
											fields_obj.timestamp = local_value.timestamp;
										}
									}
										
								
								symbol_obj = {
									markerFile: structuredClone(local_geometry._icon?.getAttribute("src")),
									markerHeight: 24,
									markerWidth: 24,
								};
								
								if (local_geometry?._popup?._content)
									fields_obj.html = local_geometry?._popup?._content;
							}
							
							//Push geometry to results
							if (return_obj[local_type])
								return_obj[local_type].push({
									geometry: local_geometry.toGeoJSON(),
									symbol: symbol_obj,
									type: local_type,
									
									title: local_geometry?.options?.title,
									...fields_obj
								});
						}
					} catch (e) { console.warn(e); }
					
					//Return all_types in order
					let all_types = Object.keys(return_obj);
					
					for (let i = 0; i < all_types.length; i++)
						results = results.concat(return_obj[all_types[i]]);
					
					//Return statement
					return results;
				});
				
				let current_scrape_time = Date.now();
				
				for (let i = 0; i < geometries.length; i++) try {
					if (!geometries[i]?.geometry?.geometry?.coordinates) continue; //Make sure coordinates exist
					
					let coord_string = JSON.stringify(geometries[i].geometry.geometry.coordinates);
					let event_id = `liveuamap_${local_region.name}_${coord_string.hashCode()}`;
					let ontology_obj = new Ontology_Event([{
						date: current_scrape_time,
						data: {
							region: local_region.name,
							region_url: local_region.url,
							...geometries[i]
						}
					}], {
						id: event_id,
						worker_type: "Liveuamap"
					});
					
					//Draw the instance immediately
					ontology_obj.draw();
					ontologies.push(ontology_obj);
				} catch (e) { this.error(e); }
				
				//Sleep to bypass rate limit
				await Blacktraffic.sleep(Math.randomNumber(10000, 15000));
			} catch (e) {
				this.error(`Error processing region ${i}:`, e);
			}
		}
		
		return ontologies;
	}
	
	async getLiveuamapRegions() {
		//Declare local instance variables
		let json_path = this.static.input_auto_regions_json;
		
		//Return statement if valid cache exists
		if (fs.existsSync(json_path)) {
			let age = Date.now() - fs.statSync(json_path).mtimeMs;
			
			if (age < this.static._update_regions_interval*1000) 
				return JSON.parse(fs.readFileSync(json_path, "utf8"));
		}
		
		//Make sure tab for worker is open
		this.log("Refreshing regions cache ...");
		let tab = await this.getTab();
		
		try {
			await tab.goto("https://liveuamap.com/", { waitUntil: "networkidle2" });
			await tab.waitForSelector(`a#menu_languages`);
			await tab.click(`a#menu_languages`);
			
			let regions = await tab.$$eval(`div.rg-list > a`, (els) => els.map((el) => ({ 
				name: el.getAttribute("title"), 
				url: el.href
			})));
			
			if (!fs.existsSync(path.dirname(json_path))) 
				fs.mkdirSync(path.dirname(json_path), { recursive: true });
			fs.writeFileSync(json_path, JSON.stringify(regions, null, 2));
			await tab.close();
			
			//Return statement
			return regions;
		} catch (e) {
			this.error("Discovery failed:", e.stack);
			await tab.close();
			
			//Return statement
			return (fs.existsSync(json_path)) ? 
				JSON.parse(fs.readFileSync(json_path, "utf8")) : [];
		}
	}
};

/**
 * String Hashing Helper
 */
if (!String.prototype.hashCode) {
	String.prototype.hashCode = function() {
		let hash = 0;
		for (let i = 0, len = this.length; i < len; i++) {
			let chr = this.charCodeAt(i);
			hash = (hash << 5) - hash + chr;
			hash |= 0;
		}
		return Math.abs(hash).toString(16);
	};
}