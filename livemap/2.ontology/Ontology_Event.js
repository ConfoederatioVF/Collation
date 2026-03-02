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
	draw() {
		// 1. Clean up existing geometries for this specific ontology instance
		if (this.geometries) {
			for (let local_geometry of this.geometries) {
				if (local_geometry && local_geometry.remove) local_geometry.remove();
			}
		}
		this.geometries = [];
		
		// 2. Resolve the current state (latest snapshot)
		let current_state = this.getState(Date.now());
		
		if (current_state && current_state.geometry) {
			try {
				// 3. Convert GeoJSON to maptalks geometry
				let m_geom = maptalks.GeoJSON.toGeometry(current_state.geometry);
				
				// 4. Apply the symbol (styling)
				if (current_state.symbol) {
					m_geom.updateSymbol(current_state.symbol);
				}
				
				// 5. Add to the designated map layer
				if (typeof map !== "undefined") {
					// Use a specific layer for Liveuamap events
					let layer = map.getLayer("liveuamap") || new maptalks.VectorLayer("liveuamap", { zIndex: 101 }).addTo(map);
					m_geom.addTo(layer);
				}
				
				// 6. Track the geometry so we can remove/update it later
				this.geometries.push(m_geom);
			} catch (e) {
				console.error(`[Ontology_Event] Failed to draw geometry for ${this.id}:`, e);
			}
		}
		
		return this.geometries;
	}
};