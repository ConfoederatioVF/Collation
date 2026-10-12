if (!global.naissance) global.naissnace = {};
naissance.BrushNodeEditor = class extends ve.Class {
	constructor () {
		super();
		
		//Declare local instance variables
		this.coords = [];
		this.mode = "Polygon";
		this.type = "add";
		this.enabled = false;
		
		this._click_listener = (e) => { this.onclick(e); };
		this._dblclick_listener = (e) => { this.ondblclick(e); };
		this._mousemove_listener = (e) => { this.onmousemove(e); };
	}
	
	addNode (coord) {
		this.coords.push(coord);
		this.draw();
	}
	
	disable () {
		this.enabled = false;
		this.coords = [];
		if (this.geometry) {
			this.geometry.remove();
			this.geometry = null;
		}
		map.off("click", this._click_listener);
		map.off("dblclick", this._dblclick_listener);
		map.off("mousemove", this._mousemove_listener);
	}
	
	draw (temp_coord) {
		if (this.geometry) this.geometry.remove();
		
		let draw_coords = [...this.coords];
		if (temp_coord) draw_coords.push(temp_coord);
		
		if (draw_coords.length < 2) return;
		
		let fill_color = (this.type === "remove") ? "rgba(240, 60, 60, 0.5)" : "rgba(255, 255, 255, 0.5)";
		let stroke_color = (this.type === "remove") ? "rgba(240, 60, 60, 1)" : "rgba(255, 255, 255, 1)";
		
		let current_mode = "Polygon";
		if (this.mode === "LineString" || this.mode === "FreeHandLineString")
			current_mode = "LineString";
		this.geometry = new maptalks[current_mode](draw_coords, {
			symbol: {
				polygonFill: fill_color,
				lineColor: stroke_color,
				lineWidth: 2
			}
		});
		
		this.geometry.addTo(main.layers.cursor_layer);
	}
	
	enable () {
		this.disable();
		this.enabled = true;
		this.type = "add";
		
		map_component.on("click", this._click_listener);
		map_component.on("dblclick", this._dblclick_listener);
		map_component.on("mousemove", this._mousemove_listener);
	}
	
	onclick (e) {
		//Declare local instance variables
		let is_line = ["FreeHandLineString", "LineString"].includes(this.mode);
		let is_node_brush = ["node", "node_override", "node_transfer"].includes(main.brush.mode);
		
		if (is_line && HTML.ctrl_pressed)
			if (HTML.ctrl_pressed)
				return; //Remove isn't valid for GeometryLine
		
		if (this.coords.length === 0) {
			if (is_line && !is_node_brush && main.brush._selected_geometry?.isOpen("instance"))
					return; //We don't want users trying to click a line to suddenly get a popup from it
			
			this.disable();
			this.enable(); //We need to make sure that the NodeEditor is active in this state
			this.type = (HTML.ctrl_pressed) ? "remove" : "add";
		}
		this.addNode(e.coordinate);
	}
	
	onmousemove (e) {
		if (this.coords.length === 0) return;
		this.draw(e.coordinate);
	}
	
	ondblclick (e) {
		if (this.coords.length < 2) return; //Internal guard clause if less than 2 coords to finish
		
		let selected_geometry = main.brush._selected_geometry;
		
		//Internal guard clause; check to make sure that ._selected_geometry is not in a provinces layer
		if (selected_geometry) {
			let layer_obj = selected_geometry.getLayer();
			if (layer_obj?._type === "provinces") {
				this.disable();
				this.enable();
				return;
			}
			
			//Call handler using .type instead of overwriting .mode
			if (naissance[selected_geometry.class_name]?.handleNodeEditorEnd)
				naissance[selected_geometry.class_name].handleNodeEditorEnd.call(selected_geometry, { geometry: this.geometry });
		}
		
		this.disable();
		this.enable();
	}
	
	update () {
		let selected_geometry = main.brush._selected_geometry;
		let is_node_brush = ["node", "node_override", "node_transfer"].includes(main.brush.mode);
		
		if (selected_geometry) {
			let is_geometry_line = selected_geometry instanceof naissance.GeometryLine;
			
			//Ensure LineString is used for lines, otherwise check node_editor_mode or default to Polygon
			if (is_node_brush || is_geometry_line) {
				this.mode = (is_geometry_line) ? "LineString" : (selected_geometry.node_editor_mode || "Polygon");
				this.enable();
			} else {
				this.disable();
			}
		} else {
			this.disable();
		}
	}
};

naissance.GeometryLine.handleNodeEditorEnd = function (arg0_e) {
	//Convert from parameters
	let e = arg0_e;
	
	//Push action to timeline based on .type
	if (main.brush.node_editor.type === "add") {
		e.geometry = main.brush.getAddLine(e.geometry);
		DALS.Timeline.parseAction("add_to_line", [{
			geometry_obj: this.id,
			add_to_line: { geometry: e.geometry.toJSON() }
		}]);
	}
	
	main.brush.node_editor.disable();
	main.brush.node_editor.enable();
};
naissance.GeometryPolygon.handleNodeEditorEnd = async function (arg0_e) {
	//Convert from parameters
	let e = arg0_e;
	
	//Declare local instance variables
	let date_range = main.interfaces.edit_brush_keyframes.getDateRange();
	
	//Transfer handler
	if (main.brush.mode === "node_transfer") {
		try {
			let from_geometry_id = main.brush.from_geometry_id;
			if (!from_geometry_id && main.brush.brush_options?.from_geometry)
				from_geometry_id = main.brush.brush_options.from_geometry.v;
			if (!from_geometry_id && main.brush.brush_options?.components_obj?.from_geometry)
				from_geometry_id = main.brush.brush_options.components_obj.from_geometry.v;
			
			let from_geometry = (from_geometry_id) ? (naissance.Geometry.instances[from_geometry_id] || naissance.Feature?.instances?.[from_geometry_id]) : null;
			if (!from_geometry && from_geometry_id) {
				let norm_id = String(from_geometry_id).replace(/\s+/g, "").toLowerCase();
				Object.iterate(naissance.Geometry.instances, (local_id, local_geom) => {
					let geom_id = String(local_id).replace(/\s+/g, "").toLowerCase();
					let geom_name = (local_geom.name) ? String(local_geom.name).replace(/\s+/g, "").toLowerCase() : "";
					if (geom_name === norm_id || geom_id === norm_id) {
						from_geometry = local_geom;
						from_geometry_id = local_id;
					}
				});
				if (!from_geometry && naissance.Feature?.instances) {
					Object.iterate(naissance.Feature.instances, (local_id, local_feat) => {
						let feat_id = String(local_id).replace(/\s+/g, "").toLowerCase();
						let feat_name = (local_feat.name) ? String(local_feat.name).replace(/\s+/g, "").toLowerCase() : "";
						if (feat_name === norm_id || feat_id === norm_id) {
							from_geometry = local_feat;
							from_geometry_id = local_id;
						}
					});
				}
			}
			
			//If a Feature was matched, resolve its active geometry
			if (from_geometry && from_geometry instanceof naissance.Feature) {
				let sub_geoms = (typeof from_geometry.getAllGeometries === "function") ?
					from_geometry.getAllGeometries() : (from_geometry.entities || []);
				for (let i = 0; i < sub_geoms.length; i++) {
					if (sub_geoms[i] instanceof naissance.GeometryPolygon || sub_geoms[i] instanceof naissance.GeometryLine) {
						from_geometry = sub_geoms[i];
						from_geometry_id = sub_geoms[i].id;
						break;
					}
				}
			}
			
			if (from_geometry) main.brush.from_geometry_id = from_geometry.id;
			
			if (!from_geometry) {
				veToast("<icon>warning</icon> No source geometry selected for node transfer.");
				main.brush.node_editor.disable();
				main.brush.node_editor.enable();
				return;
			}
			if (from_geometry.id === this.id) {
				veToast("<icon>warning</icon> Cannot transfer nodes to the same geometry.");
				main.brush.node_editor.disable();
				main.brush.node_editor.enable();
				return;
			}
			
			//Ensure history is loaded for both geometries
			if (typeof from_geometry.loadHistory === "function")
				await from_geometry.loadHistory();
			if (typeof this.loadHistory === "function")
				await this.loadHistory();
			
			//Ensure geometries are drawn or loaded
			if (!from_geometry.geometry) from_geometry.draw();
			if (!from_geometry.geometry) {
				let kf_geom = from_geometry.getGeometryKeyframeAtDate(main.date);
				if (kf_geom) from_geometry.geometry = maptalks.Geometry.fromJSON(kf_geom);
			}
			if (!from_geometry.geometry && from_geometry.value?.[0]) {
				from_geometry.geometry = maptalks.Geometry.fromJSON(from_geometry.value[0]);
			}
			if (!this.geometry) this.draw();
			if (!this.geometry) {
				let kf_geom = this.getGeometryKeyframeAtDate(main.date);
				if (kf_geom) this.geometry = maptalks.Geometry.fromJSON(kf_geom);
			}
			if (!this.geometry && this.value?.[0]) {
				this.geometry = maptalks.Geometry.fromJSON(this.value[0]);
			}
			
			if (!(from_geometry?.geometry && e?.geometry)) {
				veToast("<icon>warning</icon> Source geometry has no spatial coordinates at current date.");
				main.brush.node_editor.disable();
				main.brush.node_editor.enable();
				return;
			}
			
			let cursor_turf_geometry = Geospatiale.convertMaptalksToTurf(e.geometry);
			let ot_turf_geometry = Geospatiale.convertMaptalksToTurf(from_geometry.geometry);
			let turf_geometry = (this.geometry) ? Geospatiale.convertMaptalksToTurf(this.geometry) : null;
			
			let turf_intersection = (main.brush.node_editor.type === "add") ?
				turf.intersect(turf.featureCollection([ot_turf_geometry, cursor_turf_geometry])) :
				(turf_geometry ? turf.intersect(turf.featureCollection([turf_geometry, cursor_turf_geometry])) : null);
			
			if (!turf_intersection) {
				veToast("<icon>info</icon> No overlapping geometry found to transfer.");
				main.brush.node_editor.disable();
				main.brush.node_editor.enable();
				return;
			}
			
			//Apply simplify if configured
			if (main.brush.simplify > 0)
				turf_intersection = turf.simplify(turf_intersection, { tolerance: main.brush.simplify });
			
			//Buffer for subtraction to avoid zero-width gaps on shared boundaries
			let node_buffer_m = Math.returnSafeNumber(main.brush.node_buffer, 0);
			let buffer_km = (node_buffer_m > 0) ? (node_buffer_m / 1000) : 0.0001;
			let turf_subtraction = turf_intersection;
			try {
				let buffered = turf.buffer(turf_intersection, buffer_km, { units: "kilometers", steps: 1 });
				if (buffered) turf_subtraction = buffered;
			} catch (err) {}
			
			let maptalks_add = Geospatiale.convertTurfToMaptalks(turf_intersection);
			let maptalks_remove = Geospatiale.convertTurfToMaptalks(turf_subtraction);
			
			if (!maptalks_add) return;
			let add_json = maptalks_add.toJSON();
			let remove_json = maptalks_remove ? maptalks_remove.toJSON() : add_json;
			
			//Handle date range vs single date
			if (date_range) {
				let start_ts = Math.min(Date.getTimestamp(date_range[0]), Date.getTimestamp(date_range[1]));
				let end_ts = Math.max(Date.getTimestamp(date_range[0]), Date.getTimestamp(date_range[1]));
				
				let ts_set = new Set();
				ts_set.add(start_ts);
				
				let from_ts = from_geometry.history ? from_geometry.history.getTimestamps() : [];
				for (let i = 0; i < from_ts.length; i++)
					if (from_ts[i] >= start_ts && from_ts[i] <= end_ts)
						ts_set.add(from_ts[i]);
				
				let this_ts = this.history ? this.history.getTimestamps() : [];
				for (let i = 0; i < this_ts.length; i++)
					if (this_ts[i] >= start_ts && this_ts[i] <= end_ts)
						ts_set.add(this_ts[i]);
				
				let all_timestamps = Array.from(ts_set).sort((a, b) => a - b);
				
				for (let i = 0; i < all_timestamps.length; i++) {
					let local_ts = all_timestamps[i];
					if (main.brush.node_editor.type === "add") {
						await DALS.Timeline.parseAction("remove_from_polygon", [{
							geometry_obj: from_geometry.id,
							remove_from_polygon: { date: local_ts, geometry: remove_json }
						}], true);
						await DALS.Timeline.parseAction("add_to_polygon", [{
							geometry_obj: this.id,
							add_to_polygon: { date: local_ts, geometry: add_json }
						}], true);
					} else if (main.brush.node_editor.type === "remove") {
						await DALS.Timeline.parseAction("remove_from_polygon", [{
							geometry_obj: this.id,
							remove_from_polygon: { date: local_ts, geometry: remove_json }
						}], true);
						await DALS.Timeline.parseAction("add_to_polygon", [{
							geometry_obj: from_geometry.id,
							add_to_polygon: { date: local_ts, geometry: add_json }
						}], true);
					}
				}
			} else {
				//Single date (current date)
				if (main.brush.node_editor.type === "add") {
					await DALS.Timeline.parseAction("remove_from_polygon", [{
						geometry_obj: from_geometry.id,
						remove_from_polygon: { date: main.date, geometry: remove_json }
					}], true);
					await DALS.Timeline.parseAction("add_to_polygon", [{
						geometry_obj: this.id,
						add_to_polygon: { date: main.date, geometry: add_json }
					}], true);
				} else if (main.brush.node_editor.type === "remove") {
					await DALS.Timeline.parseAction("remove_from_polygon", [{
						geometry_obj: this.id,
						remove_from_polygon: { date: main.date, geometry: remove_json }
					}], true);
					await DALS.Timeline.parseAction("add_to_polygon", [{
						geometry_obj: from_geometry.id,
						add_to_polygon: { date: main.date, geometry: add_json }
					}], true);
				}
			}
			
			from_geometry.draw();
			this.draw();
			if (typeof UI_Leftbar !== "undefined" && UI_Leftbar.refresh) UI_Leftbar.refresh();
			veToast("<icon>check</icon> Transferred nodes successfully.");
			
		} catch (err) {
			console.error("[handleNodeEditorEnd] Error during node transfer:", err);
		}
		
		main.brush.node_editor.disable();
		main.brush.node_editor.enable();
		return;
	}
	
	//Push action to timeline for selected geometry
	if (main.brush.node_editor.type === "add") {
		e.geometry = main.brush.getAddPolygon(e.geometry);
		if (!e.geometry) console.log(`Undefined geometry:`, e.geometry);
		DALS.Timeline.parseAction("add_to_polygon", [{
			geometry_obj: this.id,
			add_to_polygon: {
				date_range: date_range,
				geometry: e.geometry.toJSON()
			},
			simplify_polygon: {
				date_range: date_range,
				tolerance: (main.brush.simplify > 0 && main.brush.simplify_applies_to_polygon) ?
					main.brush.simplify : undefined
			}
		}]); //Add cut to target polygon
	} else if (main.brush.node_editor.type === "remove") {
		e.geometry = main.brush.getRemovePolygon(e.geometry);
		DALS.Timeline.parseAction("remove_from_polygon", [{
			geometry_obj: this.id,
			remove_from_polygon: {
				date_range: date_range,
				geometry: e.geometry.toJSON()
			}
		}]);
	}
	
	main.brush.node_editor.disable();
	main.brush.node_editor.enable();
};