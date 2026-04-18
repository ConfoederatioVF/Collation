global.polities_Cliopatria_UI = class {
	/**
	 * @type {string}
	 */
	static input_path = `${h1}/polities_Cliopatria/cliopatria.geojson/cliopatria_polities_only.geojson`;
	
	constructor (arg0_options) {
		//Declare local instance variables
		this.geometries = [];
		this.is_dataset = true;
	}
	
	clear () {
		//Iterate over all this.geometries and remove them from the map
		for (let i = 0; i < this.geometries.length; i++)
			this.geometries[i].remove();
		this.geometries = [];
	}
	
	draw (arg0_date) {
		//Convert from parameters
		let date_obj = (arg0_date) ? arg0_date : Date.getCurrentDate();
		
		//Declare local instance variables
		this.geojson_obj = JSON.parse(fs.readFileSync(polities_Cliopatria_UI.input_path, "utf8"));
		let label_geometries = [];
		let map_defines = config.defines.map;
		
		//Clear map first
		this.clear();
		
		//Iterate over geojson_obj.features and if the date is between [.properties.FromYear, .properties.ToYear], append it to the map, inclusive
		for (let i = 0; i < this.geojson_obj.features.length; i++) {
			let local_feature = this.geojson_obj.features[i];
			let local_feature_properties = this.geojson_obj.features[i].properties;
			
			if (local_feature_properties)
				if (date_obj.year >= local_feature_properties.FromYear && date_obj.year <= local_feature_properties.ToYear) {
					let local_geometry = new maptalks.GeoJSON.toGeometry(local_feature);
					let local_properties = local_geometry.properties;
					let turf_simplify = turf.simplify(Geospatiale.convertMaptalksToTurf(local_geometry), { tolerance: 0.1 });
					
					let optimised_poi = Geospatiale.getPoleOfInaccessibility(turf_simplify);
					
					if (local_geometry.properties) {
						let local_fill_colour = local_properties.fill_colour;
						
						local_geometry.updateSymbol({
							lineWidth: 1,
							polygonFill: `rgb(${local_fill_colour[0]},${local_fill_colour[1]},${local_fill_colour[2]})`,
							polygonOpacity: 0.5
						});
						local_geometry.addEventListener("click", (e) => {
							//if (main.settings.disable_mapmode_interactivity) return;
							if (this.polity_window) this.polity_window.close();
							this.polity_window = veWindow({
								actions_bar: veRawInterface({
									move_geometry_to_brush: veButton(() => {
										let selected_geometry = main.brush.selected_geometry;
										
										if (selected_geometry && selected_geometry instanceof naissance.GeometryPolygon) {
											DALS.Timeline.parseAction({
												options: { name: "Add to Polygon", key: "add_to_polygon" },
												value: [{
													type: "GeometryPolygon",
													
													geometry_id: selected_geometry.id,
													set_polygon: { geometry: local_geometry.toJSON() }
												}]
											});
										} else {
											veToast(`<icon>warning</icon> You must select a GeometryPolygon before being able to copy this geometry.`);
										}
									}, { name: "Move Geometry to Brush" })
								}, {
									style: { display: "flex" }
								}),
								description: veHTML([
									`<b>Components:</b> ${local_properties.Components}`,
									`<b>Member of:</b> ${local_properties.MemberOf}`,
									`<b>Geometry Domain:</b> ${local_properties.FromYear}-${local_properties.ToYear}`,
									`<b>Type:</b> ${local_properties.Type}`,
									`<b>Pole of Inaccessibility:</b> ${[
										`Lat: ${Math.roundNumber(local_properties.poi[0], 2)}`,
										`Lng: ${Math.roundNumber(local_properties.poi[1], 2)}`
									].join(", ")}`
								].join("<br>"))
							}, {
								name: local_properties.Name,
								can_rename: false,
								width: "16rem"
							});
						});
						
						let local_marker;
						if (local_properties.poi)
							local_marker = new maptalks.Marker([optimised_poi[1], optimised_poi[0]], {
								symbol: {
									...map_defines.default_label_symbol,
									textName: local_properties.Name
								}
							});
						
						this.geometries.push(local_geometry);
						if (local_marker)
							label_geometries.push(local_marker);
					}
				}
		}
		this.geometries = this.geometries.concat(label_geometries);
		this.geojson_obj = null; //Free memory
	}
};