/**
 * Represents a geographical event scraped from Liveuamap.
 * @extends Ontology
 */
global.Ontology_Event = class extends Ontology {
	constructor (arg0_state, arg1_options) {
		// Pass 'Event' as the type to the base Ontology class
		super("Event", arg0_state, arg1_options);
	}
	
	/**
	 * Overrides the draw method to plot the current state onto the map.
	 */
	draw () {
		// 1. Clean up existing geometries for this specific ontology instance
		if (this.geometries) {
			for (let local_geometry of this.geometries) {
				if (local_geometry && local_geometry.remove) local_geometry.remove();
			}
		}
		this.geometries = [];
		
		// 2. Resolve the current state (latest snapshot)
		let current_state = this.getState(Date.now());
		let skip_draw = false;
		
		if (current_state) try {
			if (current_state.type === "point" && Date.getDaysAgo(current_state.timestamp) > 2) 
				skip_draw = true;
		} catch (e) {}
		
		if (current_state && current_state.geometry && !skip_draw) {
			try {
				// 3. Convert GeoJSON to maptalks geometry
				let geometry = maptalks.GeoJSON.toGeometry(current_state.geometry);
				
				// 4. Apply the symbol (styling)
				if (current_state.symbol) {
					geometry.updateSymbol(current_state.symbol);
				}
				geometry.addEventListener("click", (e) => {
					if (!current_state.title && current_state.html) current_state.title = current_state.html; //Accept HTML as fallback
					if (current_state.title) {
						//Fetch name_string first
						let name_string = (current_state.timestamp !== undefined) ?
							(new Date(current_state.timestamp*1000)).toLocaleString() : "Unknown Time";
						
						let image_string = (current_state?.symbol?.markerFile) ?
							`<img src = "${current_state.symbol.markerFile}" height = "24" style = "vertical-align: middle;"> ` : "";
						let window_html = [
							`${current_state.title}`,
							"",
							`Source: ${(current_state.source) ? `<a href = "${current_state.source}">${current_state.source}</a>` : "None"}`
						];
						if (current_state.image) 
							window_html.push(`Image: <a href = "${current_state.image}">${current_state.image}</a>`);
						
						try {
							veWindow(veHTML(window_html.join("<br>"), {
								style: { overflowWrap: "break-word" }
							}), {
								name: `${image_string}${name_string}`,
								name_class: "fullbright",
								can_rename: false,
								do_not_wrap: true,
								width: "20rem"
							});
						} catch (e) { console.error(e); }
					}
				});
				
				// 5. Add to the designated map layer
				if (typeof map !== "undefined") {
					// Use a specific layer for Liveuamap events
					let layer = map.getLayer("liveuamap") || new maptalks.VectorLayer("liveuamap", { zIndex: 101 }).addTo(map);
					geometry.addTo(layer);
				}
				
				// 6. Track the geometry so we can remove/update it later
				this.geometries.push(geometry);
			} catch (e) {
				console.error(`[Ontology_Event] Failed to draw geometry for ${this.id}:`, e);
			}
		}
		
		return this.geometries;
	}
};