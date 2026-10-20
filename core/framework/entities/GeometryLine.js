if (!global.naissance) global.naissance = {};

naissance.GeometryLine = class extends naissance.Geometry {
	static hierarchy_symbol = {
		icon: "polyline",
		name: "Line",
		
		colour: "stroke"
	};
	static labelling_options = {
		autolabel_function: (naissance_obj) => {
			if (naissance_obj.geometry.getGeometries) {
				let all_geometries = naissance_obj.geometry.getGeometries();
				
				for (let i = 0; i < all_geometries.length; i++)  {
					let local_label_geometry = new maptalks.Marker(all_geometries[i].getCenter());
					naissance_obj.label_geometries.push(local_label_geometry);
				}
			} else {
				let local_label_geometry = new maptalks.Marker(naissance_obj.geometry.getCenter());
				naissance_obj.label_geometries.push(local_label_geometry);
			}
		}
	};
	
	constructor (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		super(options);
		
		//Declare local instance variables
		this.class_name = "GeometryLine";
		this.node_editor_mode = "LineString";
		
		//Add keyframe with default brush symbol upon instantiation
		if (!options.is_import) {
			let brush_symbol = main.brush.getBrushSymbol();
			if (brush_symbol)
				this.addKeyframe(main.date, undefined, brush_symbol);
		}
		
		//KEEP AT BOTTOM!
		this.updateOwner();
	}
	
	draw () {
		let main_obj = (typeof main !== "undefined") ? main : (globalThis.main || global.main);
		let map_obj = (typeof map !== "undefined") ? map : (globalThis.map || global.map);
		
		//Declare local instance variables
		let derender_geometry = false;
		
		//Remove geometry first to handle it
		if (this.selected_geometry) this.selected_geometry.remove();
		this.selected_geometry = undefined;
		
		//1. Set this.value from current relative keyframe if present in history
		let has_local_history = (this.history?.keyframes && Object.keys(this.history.keyframes).length > 0);
		if (has_local_history) {
			if (this.history._hasTimestampAfter && this.history._hasTimestampAfter(main_obj?.timestamp)) {
				let kf_obj = this.history.getKeyframe({ 
					date: main_obj?.timestamp,
					guaranteed_indexes: [1]
				});
				this.value = (kf_obj?.value) ? kf_obj.value : null;
				if (this.value && this.value[1])
					this.value[1] = this.getSymbol(this.value[1]);
			} else {
				this.value = null;
			}
		}
		
		if (this.value === undefined || this.value === null || this.value.length === 0 || this._is_visible === false) 
			derender_geometry = true;
		
		//2. Check any cause for derendering
		if (this.value && (this.value[0] === null || this.value[0] === undefined || this.value[0] === "undefined" || this.value[0] === "null" || this.value[0] === "")) derender_geometry = true; //Coords are null, derender geometry
		if (this.value && this.value[2]) {
			if (this.value[2].hidden) derender_geometry = true;
			if (this.value[2].max_zoom && map_obj?.getZoom && map_obj.getZoom() > this.value[2].max_zoom) derender_geometry = true;
			if (this.value[2].min_zoom && map_obj?.getZoom && map_obj.getZoom() < this.value[2].min_zoom) derender_geometry = true;
		}
		
		//3. Draw this.geometry, this.label from this.value onto map
		if (!derender_geometry) {
			try {
				if (this.geometry) this.geometry.remove();
				if (this.label_geometries)
					for (let i = this.label_geometries.length - 1; i >= 0; i--) {
						this.label_geometries[i].remove();
						this.label_geometries.splice(i, 1);
					}
				if (this.selected_geometry) this.selected_geometry.remove();
				
				//Draw this.geometry, this.label_geometries, this.selected_geometry
				if (this.value[0] && this.value[0] !== "undefined" && this.value[0] !== "null") {
					let raw_geom = this.value[0];
					if (typeof raw_geom === "string") {
						try {
							raw_geom = JSON.parse(raw_geom);
						} catch (parse_err) {
							raw_geom = null;
						}
					}
					
					if (raw_geom && typeof raw_geom === "object") {
						this.geometry = maptalks.Geometry.fromJSON(raw_geom);
					}
					if (this.geometry) {
						let symbol_obj = { ...(this.value[1] || {}) };
						if (this.selected) {
							symbol_obj.lineColor = "rgb(255, 255, 0)";
							symbol_obj.lineWidth = 4;
							symbol_obj.lineOpacity = 0.8;
							if (main.brush?.selected_geometry?.id !== this.id)
								symbol_obj.lineDasharray = [10, 10, 10];
						}
						this.geometry.setSymbol(symbol_obj);
						if (main_obj?.layers?.entity_layer)
							main_obj.layers.entity_layer.addGeometry(this.geometry);
						
						this.drawLabels(); //Draw labels
					}
				}
			} catch (e) { console.error(e); }
		}
		
		//4. Draw this.selected_geometry (zero-copy: selection symbol applied directly to this.geometry)
		this.selected_geometry = undefined;
		
		//5. Add bindings
		if (this.geometry) {
			this.history.draw(this.keyframes_ui);
			
			this.handleOnclick({
				special_function: (e) => {
					if (
						HTML.ctrl_pressed &&
						main.brush._selected_geometry?.id === this.id
						&& e.pickGeometryIndex !== undefined
					) {
						//Remove this index from the line instead
						DALS.Timeline.parseAction("remove_from_line", [{
							geometry_obj: main.brush._selected_geometry.id,
							remove_from_line: e.pickGeometryIndex
						}]);
					}
				}
			});
		}
		
		//6. Derender geometry handler
		if (derender_geometry) {
			if (this.geometry) this.geometry.remove();
			if (this.label_geometries)
				for (let i = 0; i < this.label_geometries.length; i++)
					this.label_geometries[i].remove();
			if (this.selected_geometry) this.selected_geometry.remove();
		}
	}
	
	drawUI () {
		//Return statement
		return {
			edit_symbol_ui: veInterface({
				edit_label: new UI_LabelSymbol(main.settings.default_label_symbol, {
					name: "Label",
					enable_custom_labels: true,
					geometry_obj: this,
					special_function: (v) => UI_EditSelectedGeometries._makeSetSymbol({ label_symbol: v, _id: this.id })
				}),
				edit_stroke: new UI_LineSymbol(main.settings.default_line_symbol, {
					name: "Stroke",
					special_function: (v) => UI_EditSelectedGeometries._makeSetSymbol({ ...v, _id: this.id })
				})
			}, { name: "Edit Symbol" })
		};
	}
};