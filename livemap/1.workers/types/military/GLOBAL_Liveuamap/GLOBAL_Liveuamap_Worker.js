global.GLOBAL_Liveuamap_Worker = class extends Blacktraffic.Worker {
	static bf = `${l1m}GLOBAL_Liveuamap/`;
	static input_auto_regions_json = path.join(this.bf, "Liveuamap_auto_regions.json");
	static _update_regions_interval = 86400*7; //Once a week
	
	constructor(arg0_options) {
		let options = arg0_options || {};
		let target_interval = options.interval || 3600;
		
		super("Liveuamap", {
			...options,
			interval: 0,
			log_channel: "Liveuamap_Scraper",
		});
		
		this.options.top_regions = Math.returnSafeNumber(options.top_regions, -1);
		this.static = GLOBAL_Liveuamap_Worker;
		this.layer = null;
		
		this.options.interval = target_interval;
		if (this.is_enabled && this.options.interval > 0) this.startInterval();
	}
	
	async execute (tab, instance) {
		let all_regions = await this.getLiveuamapRegions();
		let regions_threshold = this.options.top_regions > 0 ? this.options.top_regions : all_regions.length;
		let ontologies = [];
		
		if (!this.layer && typeof map !== "undefined") {
			this.layer = new maptalks.VectorLayer("liveuamap", { zIndex: 101 }).addTo(map);
		}
		
		const webapi = Blacktraffic.AgentBrowser.webapi;
		// We still call captureMaps here to ensure it's bound before Leaflet initializes
		await tab.evaluateOnNewDocument(webapi.Leaflet.captureMaps);
		
		for (let i = 0; i < regions_threshold; i++) {
			try {
				let local_region = all_regions[i];
				if (!local_region) continue;
				
				this.log(`[${i + 1}/${regions_threshold}] Polling region: ${local_region.name} ..`);
				
				await tab.goto(local_region.url, { waitUntil: "networkidle2" });
				await Blacktraffic.sleep(Math.randomNumber(2000, 4000));
				
				let is_paid = await tab.evaluate(() => {
					let modal = document.querySelector(`.modalWrapCont`);
					return modal && modal.innerHTML.includes("in free version");
				});
				
				if (is_paid) {
					this.warn(`Skipping ${local_region.name}: Blocked by free version limit.`);
					continue;
				}
				
				let geometries = await tab.evaluate(function () {
					// Verify that webapi was successfully injected by AgentBrowser
					if (typeof webapi === "undefined" || !webapi.Leaflet) return [];
					if (typeof getMaps !== "function") return [];
					
					let current_map = getMaps()[0];
					if (!current_map) return [];
					
					let layers = current_map._layers;
					let results = [];
					
					for (let key in layers) {
						let layer = layers[key];
						
						// Reference the function via its full path in the webapi object
						let type = webapi.Leaflet.getGeometryType(layer);
						let opt = layer.options;
						
						if (["polygon", "line"].includes(type)) {
							results.push({
								geometry: layer.toGeoJSON(),
								symbol: {
									polygonFill: opt.fillColor,
									polygonOpacity: parseFloat(opt.fillOpacity),
									lineColor: opt.color,
									lineOpacity: parseFloat(opt.opacity),
									lineWidth: parseFloat(opt.weight),
								},
								type: type,
							});
						} else if (type === "point") {
							let icon = layer._icon ? layer._icon.getAttribute("src") : null;
							results.push({
								geometry: layer.toGeoJSON(),
								symbol: {
									markerHeight: 24,
									markerWidth: 24,
									markerFile: icon,
								},
								type: type,
							});
						}
					}
					return results;
				});
				
				for (let geom of geometries) {
					if (this.layer) {
						let m_geom = maptalks.GeoJSON.toGeometry(geom.geometry);
						m_geom.updateSymbol(geom.symbol);
						m_geom.addTo(this.layer);
					}
					ontologies.push(geom);
				}
				
				await Blacktraffic.sleep(Math.randomNumber(10000, 20000));
			} catch (e) {
				this.error(`Error processing region at index ${i}:`, e.message);
			}
		}
		
		return ontologies;
	}
	
	async getLiveuamapRegions () {
		const json_path = this.constructor.input_auto_regions_json;
		let refresh_cache = false;
		
		if (!fs.existsSync(json_path)) {
			refresh_cache = true;
		} else {
			let stats = fs.statSync(json_path);
			let age_ms = Date.now() - stats.mtimeMs;
			if (age_ms >= this.constructor._update_regions_interval * 1000) refresh_cache = true;
		}
		
		if (!refresh_cache) {
			return JSON.parse(fs.readFileSync(json_path, "utf8"));
		} else {
			this.log("Regions cache stale. Fetching new region list...");
			let browser = await this.getBrowser();
			let temp_tab = await browser.openTab("liveuamap_discovery");
			
			try {
				await temp_tab.goto("https://liveuamap.com/", { waitUntil: "networkidle2" });
				await temp_tab.waitForSelector(`a#menu_languages`);
				await temp_tab.click(`a#menu_languages`);
				
				let regions = await temp_tab.$$eval(`div.rg-list > a`, (els) => {
					return els.map((el) => ({
						name: el.getAttribute("title"),
						url: el.href,
					}));
				});
				
				if (!fs.existsSync(path.dirname(json_path))) fs.mkdirSync(path.dirname(json_path), { recursive: true });
				fs.writeFileSync(json_path, JSON.stringify(regions, null, 2));
				
				await temp_tab.close();
				return regions;
			} catch (e) {
				this.error("Failed to discover Liveuamap regions:", e.stack);
				await temp_tab.close();
				return fs.existsSync(json_path) ? JSON.parse(fs.readFileSync(json_path, "utf8")) : [];
			}
		}
	}
};