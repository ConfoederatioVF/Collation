if (!global.naissance) global.naissance = {};
naissance.Renderer = class extends ve.Class {
	constructor () {
		super();
		
		this.handleEvents();
	}
	
	/**
	 * Completely removes all map elements (geometry, selection, labels) and clears entity state.
	 * - Method of: {@link naissance.Renderer}
	 *
	 * @param {Object} arg0_instance
	 */
	derenderEntity (arg0_instance) {
		//Convert from parameters
		let inst = arg0_instance;
		
		if (!inst) return;
		
		if (inst.geometry) {
			try { inst.geometry.remove(); } catch (e) {}
			inst.geometry = undefined;
		}
		if (inst.selected_geometry) {
			try { inst.selected_geometry.remove(); } catch (e) {}
			inst.selected_geometry = undefined;
		}
		if (inst.label_geometries && Array.isArray(inst.label_geometries)) {
			for (let i = inst.label_geometries.length - 1; i >= 0; i--) {
				try { inst.label_geometries[i].remove(); } catch (e) {}
			}
			inst.label_geometries = [];
		}
		inst.value = undefined;
	}
	
	/**
	 * Handles Render events, particularly for zoom-related visibility.
	 * - Method of: {@link naissance.Renderer}
	 */
	handleEvents () {
		if (global.map_component?.on) {
			map_component.on("zoomend", () => {
				this.update();
			});
			map_component.on("moveend", () => {
				this.update();
			});
		}
	}
	
	/**
	 * Returns the ordered z-indexes of all Geometries within each Feature based on {@link UI_LeftbarHierarchy}.
	 * - Method of: {@link naissance.Renderer}
	 */
	getRenderingOrder (arg0_entity_obj) {
		//Convert from parameters
		let entity_obj = (arg0_entity_obj) ? arg0_entity_obj : undefined;
		
		//Declare local instance variables
		let rendering_order = [];
		
		//1. Base Hierarchy handling
		if (!entity_obj) {
			//First, collect all top-level features into a temporary static array
			let top_level_features = [];
			Object.iterate(naissance.Feature.instances, (local_key, local_feature) => {
				if (!local_feature.parent) top_level_features.push(local_feature);
			});
			
			//Now, iterate over the static list of top-level features to build the final order
			for (let i = 0; i < top_level_features.length; i++) {
				let local_feature = top_level_features[i];
				
				//Add the feature itself to the order
				rendering_order.push(local_feature);
				//Then, recursively get and concatenate all its descendants
				rendering_order = rendering_order.concat(this.getRenderingOrder(local_feature));
			}
			
			//Iterate over all naissance.Geometry.instances and append top-level ones to the end
			Object.iterate(naissance.Geometry.instances, (local_key, local_geometry) => {
				if (!local_geometry.parent) rendering_order.push(local_geometry);
			});
		}
		//2. naissance.Feature handling (Recursive step)
		else {
			//(Real Groups) naissance.Group, naissance.Layer handling
			if (entity_obj.entities) {
				for (let i = 0; i < entity_obj.entities.length; i++) {
					let local_entity = entity_obj.entities[i];
					
					rendering_order.push(local_entity);
					if (local_entity.entities || local_entity._entities)
						rendering_order = rendering_order.concat(this.getRenderingOrder(local_entity));
				}
			}
			//(Pseudo-Groups) naissance.SketchMap handling
			else if (entity_obj._entities) {
				for (let i = 0; i < entity_obj._entities.length; i++) {
					let local_geometry = entity_obj._entities[i];
					
					rendering_order.push(local_geometry);
				}
			}
		}
		
		//Return statement
		return rendering_order;
	}
	
	/**
	 * Returns a list of all unique timestamps in the current global state.
	 * - Method of: {@link naissance.Renderer}
	 * 
	 * @returns {number[]}
	 */
	getTimestamps () {
		//Declare local instance variables
		let all_timestamps = [];
		
		//Iterate over all naissance.Feature.instances with no .parent
		Object.iterate(naissance.Feature.instances, (local_key, local_feature) => {
			if (!local_feature.parent) 
				all_timestamps = Array.strictUnique(all_timestamps, local_feature.getTimestamps());
		});
		
		//Iterate over all naissance.Geometry.instances with no parent
		Object.iterate(naissance.Geometry.instances, (local_key, local_geometry) => {
			if (!local_geometry.parent) 
				all_timestamps = Array.strictUnique(all_timestamps, local_geometry.history.getTimestamps());
		})
		
		//Return statement
		return all_timestamps.sort((a, b) => a - b);
	}
	
	/**
	 * Draws all Features/Geometries in order by calling their draw function,
	 * with requestAnimationFrame throttling and viewport spatial streaming when in DB mode.
	 * - Method of: {@link naissance.Renderer}
	 */
	update () {
		if (this.raf_handle && typeof cancelAnimationFrame === "function")
			cancelAnimationFrame(this.raf_handle);
		
		let update_callback = () => {
			this.raf_handle = null;
			this._update_id = (this._update_id || 0) + 1;
			let current_update_id = this._update_id;
			this.active_symbol_functions = (naissance.Mapmode?.getActiveSymbolFunctions) ?
				naissance.Mapmode.getActiveSymbolFunctions() : [];
			
			//1. In-memory instances rendering (loaded via DALS.fromJSON / editor state)
			let rendering_order = this.getRenderingOrder();
			
			if (rendering_order.length > 0 && !global.ve?.ndjson_file_path) {
				for (let i = 0; i < rendering_order.length; i++)
					if (rendering_order[i].draw)
						rendering_order[i].draw();
				return;
			}
			
			//If user has locally edited/created in-memory instances alongside DB shards, draw them
			if (rendering_order.length > 0) {
				for (let i = 0; i < rendering_order.length; i++) {
					let inst = rendering_order[i];
					let has_local_history = (inst.history?.keyframes && Object.keys(inst.history.keyframes).length > 0);
					if (has_local_history && inst.draw)
						inst.draw();
				}
			}
			
			//2. Viewport-culled streaming differencing when DB has loaded shards
			if (global.ve?.ndjson_file_path && global.db?.diffBBox) {
				(async () => {
					try {
						let bbox;
						let current_map = (typeof map !== "undefined") ? map : (globalThis.map || global.map);
						let zoom = (current_map?.getZoom) ? current_map.getZoom() : 0;
						
						if (current_map?.getExtent && zoom > 2) {
							let extent = current_map.getExtent();
							if (extent) bbox = [extent.xmin, extent.ymin, extent.xmax, extent.ymax];
						}
						
						let main_obj = (typeof main !== "undefined") ? main : (globalThis.main || global.main);
						let timestamp = (main_obj?.timestamp !== undefined) ? main_obj.timestamp :
							(main_obj?.date ? Date.getTimestamp(main_obj.date) : 0);
						
						let visible_diffs = await db.diffBBox({ bbox: bbox, timestamp: timestamp, zoom: zoom });
						
						//Guard clause against stale out-of-order async responses during rapid scrubbing
						if (this._update_id !== current_update_id) return;
						
						let visible_ids = new Set();
						if (!this.rendered_entities) this.rendered_entities = new Map();
						
						for (let i = 0; i < visible_diffs.length; i++) {
							let diff = visible_diffs[i];
							let id = diff.id || diff.key;
							
							if (!diff.value || !Array.isArray(diff.value) || diff.value.length === 0 || !diff.value[0]) {
								let inst = this.rendered_entities.get(id) || naissance.Geometry?.instances?.[id];
								if (inst) {
									this.derenderEntity(inst);
									this.rendered_entities.delete(id);
								}
								continue;
							}
							
							visible_ids.add(id);
							let inst = this.rendered_entities.get(id);
							if (!inst && naissance.Geometry?.instances?.[id]) {
								inst = naissance.Geometry.instances[id];
								this.rendered_entities.set(id, inst);
							}
							if (!inst && diff.class_name && naissance[diff.class_name]) {
								inst = new naissance[diff.class_name]({ is_import: true });
								inst.setID(id);
								this.rendered_entities.set(id, inst);
							}
							
							if (inst) {
								inst.value = diff.value;
								if (inst.draw) inst.draw();
							}
						}
						
						this.rendered_entities.forEach((inst, id) => {
							if (!visible_ids.has(id)) {
								this.derenderEntity(inst);
								this.rendered_entities.delete(id);
							}
						});
					} catch (e) {
						console.error("[Renderer] diffBBox streaming error:", e);
					}
				})();
			}
		};
		
		if (typeof requestAnimationFrame === "function") {
			this.raf_handle = requestAnimationFrame(update_callback);
		} else {
			update_callback();
		}
	}
	
	static getAllTags () {
		//Declare local instance variables
		let all_tags = [];
		
		//Iterate over all naissance.Geometry.instances and fetch their tags
		Object.iterate(naissance.Geometry.instances, (local_key, local_value) => {
			if (local_value?.metadata?.tags)
				all_tags = [...new Set([...all_tags, ...local_value.metadata.tags])];
		});
		
		//Return statement
		return all_tags;
	}
	
	static getDefaultLabelSymbol () {
		//Declare local instance variables
		let map_defines = config.defines.map;
		
		let default_maptalks_label_keys = map_defines.default_maptalks_label_keys;
		let maptalks_label_obj = {};
		
		for (let i = 0; i < default_maptalks_label_keys.length; i++)
			maptalks_label_obj[default_maptalks_label_keys[i]] = map_defines.default_maptalks_symbol[default_maptalks_label_keys[i]];
		
		//Return statement; diff main.settings.default_label_symbol and config.defines.map.default_maptalks_symbol
		return {
			...maptalks_label_obj,
			...main.settings.default_label_symbol
		};
	}
	
	static getDefaultSymbol (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		if (!options.exclude) options.exclude = [];
		
		//Declare local instance variables
		let map_defines = config.defines.map;
		
		let default_maptalks_symbol = map_defines.default_maptalks_symbol;
		let default_symbol_obj = {
			...((!options.exclude.includes("line")) ? main.settings.default_line_symbol : {}),
			...((!options.exclude.includes("point")) ? main.settings.default_point_symbol : {}),
			...((!options.exclude.includes("polygon")) ? main.settings.default_polygon_symbol : {}),
		};
		
		//Iterate over default_symbol_obj; if same as corresponding default_maptalks_symbol, remove it
		Object.iterate(default_symbol_obj, (local_key, local_value) => {
			if (local_value === default_maptalks_symbol[local_key])
				delete default_symbol_obj[local_key];
		});
		
		//Return statement
		return default_symbol_obj;
	}
	
	static toggleUI () {
		let all_interface_els = document.querySelectorAll(`#ve-overlay > .ve`);
		naissance.Renderer.hide_ui = (!naissance.Renderer.hide_ui);
		
		if (naissance.Renderer.hide_ui) {
			for (let i = 0; i < all_interface_els.length; i++) {
				if (all_interface_els[i].getAttribute("data-do-not-toggle-ui")) continue;
				let local_display = all_interface_els[i].style.display;
				
				if (local_display !== "")
					all_interface_els[i].setAttribute("data-display", JSON.parse(JSON.stringify(all_interface_els[i].style.display)));
				all_interface_els[i].style.display = "none";
			}
		} else {
			for (let i = 0; i < all_interface_els.length; i++) {
				let local_data_display = all_interface_els[i].getAttribute("data-display");
				
				all_interface_els[i].style.display = (local_data_display) ? local_data_display : "";
				all_interface_els[i].removeAttribute("data-display");
			}
		}
	}
};