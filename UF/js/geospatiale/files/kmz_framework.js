global.GeoKMZ = class { //[WIP] - This needs to be cleaned up so that KMZ Layers are actually useable from Maptalks
	constructor (arg0_kmz_file) {
		//Convert from parameters
		let kmz_file = arg0_kmz_file;
		
		//Declare local instance variables
		this.leaflet_html = document.createElement("div");
		this.map = L.map(this.leaflet_html);
		
		//Load KMZ
		this.geometries = [];
		this.layer = new maptalks.VectorLayer(kmz_file).addTo(map);
		
		//Populate this.kmz
		this.kmz = L.kmzLayer().addTo(this.map);
		this.kmz.load(kmz_file);
		this.kmz.on("load", (e) => {
			Object.iterate(e.layer._layers, (local_key, local_value) => {
				let geometry_type = Geospatiale.getLeafletGeometryType(local_value);
				
				//Check geometry_type
				if (["polygon", "line"].includes(geometry_type)) {
					this.geometries.push({
						geometry: local_value.toGeoJSON(),
						symbol: Geospatiale.convertLeafletSymbolToMaptalks(local_value.options),
						type: geometry_type
					});
				} else if (geometry_type === "point") {
					let icon_url;
						try { icon_url = local_value.options.iconUrl; } catch (e) {}
					let popup_title;
						try { popup_title = local_value._tooltip._content; } catch (e) {}
					let popup_description;
						try { popup_description = local_value._popup._content; } catch (e) {}
					
					this.geometries.push({
						geometry: local_value.toGeoJSON(),
						properties: {
							popup_title: popup_title,
							popup_description: popup_description
						},
						symbol: {
							...Geospatiale.convertLeafletSymbolToMaptalks(local_value.options),
							markerFile: icon_url
						},
						type: geometry_type
					});
				}
			});
			
			//Iterate over all this.geometries and add it to the map
			for (let i = 0; i < this.geometries.length; i++) {
				let local_geometry = maptalks.GeoJSON.toGeometry(this.geometries[i].geometry);
					try {
						local_geometry.setInfoWindow({
							title: this.geometries[i].properties.popup_title,
							content: this.geometries[i].properties.popup_description
						});
					} catch (e) {}
					local_geometry.updateSymbol(this.geometries[i].symbol);
					local_geometry.addTo(this.layer);
			}
		});
	}
};